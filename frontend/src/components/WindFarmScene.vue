<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'

const canvasRef = ref<HTMLCanvasElement | null>(null)

let animId = 0
let renderer: THREE.WebGLRenderer
let composer: EffectComposer
let controls: OrbitControls
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let clock: THREE.Clock
let oceanMesh: THREE.Mesh
let oceanBase: Float32Array
const bladeGroups: THREE.Object3D[] = []
let modelGroup: THREE.Group

onMounted(async () => {
  const canvas = canvasRef.value
  if (!canvas) return

  // ── Renderer (透明，让效果图背景透出) ──
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.2

  // ── Scene ──
  scene = new THREE.Scene()
  // 透明背景，让 CSS 层效果图透出
  scene.fog = new THREE.FogExp2(0x020b1a, 0.00015)

  // ── Camera ──
  camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 1, 300)
  camera.position.set(18, 12, 20)
  camera.lookAt(0, 3, -2)

  // ── Controls ──
  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 3, -2)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 8
  controls.maxDistance = 50
  controls.maxPolarAngle = Math.PI * 0.48
  controls.minPolarAngle = 0.2
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.15
  controls.update()

  // ── Lighting ──
  const hemiLight = new THREE.HemisphereLight(0x8899cc, 0x223344, 0.6)
  scene.add(hemiLight)

  const ambient = new THREE.AmbientLight(0x334466, 0.5)
  scene.add(ambient)

  const sun = new THREE.DirectionalLight(0xffeedd, 4.0)
  sun.position.set(30, 25, 10)
  sun.castShadow = true
  sun.shadow.mapSize.width = 2048
  sun.shadow.mapSize.height = 2048
  sun.shadow.camera.near = 0.5
  sun.shadow.camera.far = 120
  sun.shadow.camera.left = -30
  sun.shadow.camera.right = 30
  sun.shadow.camera.top = 20
  sun.shadow.camera.bottom = -20
  sun.shadow.bias = -0.0001
  scene.add(sun)

  // ── Sky (半透明渐变球，让效果图背景透出) ──
  const skyGeo = new THREE.SphereGeometry(60, 64, 32)
  const skyMat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor1: { value: new THREE.Color(0x0a1a3a) },
      uColor2: { value: new THREE.Color(0x1a3050) },
      uColor3: { value: new THREE.Color(0x2a4a6a) },
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorldPos;
      void main() {
        vec4 worldPos = modelMatrix * vec4(position, 1.0);
        vWorldPos = worldPos.xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      varying vec3 vWorldPos;
      uniform vec3 uColor1;
      uniform vec3 uColor2;
      uniform vec3 uColor3;
      void main() {
        float h = normalize(vWorldPos).y;
        float t = smoothstep(-0.1, 0.35, h);
        vec3 col = mix(uColor1, uColor2, t);
        col = mix(col, uColor3, smoothstep(0.35, 0.7, h));
        gl_FragColor = vec4(col, 0.35);
      }
    `,
    side: THREE.BackSide,
    depthWrite: false,
    transparent: true,
  })
  const sky = new THREE.Mesh(skyGeo, skyMat)
  sky.renderOrder = -1
  scene.add(sky)

  // ── Stars ──
  const starsGeo = new THREE.BufferGeometry()
  const starCount = 800
  const starArr = new Float32Array(starCount * 3)
  for (let i = 0; i < starArr.length; i += 3) {
    const theta = Math.random() * Math.PI * 2
    const phi = Math.random() * Math.PI * 0.4
    const r = 45 + Math.random() * 15
    starArr[i] = Math.cos(theta) * Math.cos(phi) * r
    starArr[i + 1] = Math.sin(phi) * r + 8
    starArr[i + 2] = Math.sin(theta) * Math.cos(phi) * r
  }
  starsGeo.setAttribute('position', new THREE.BufferAttribute(starArr, 3))
  const starsMat = new THREE.PointsMaterial({
    color: 0xcceeff,
    size: 0.08,
    transparent: true,
    opacity: 0.7,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  scene.add(new THREE.Points(starsGeo, starsMat))

  // ── Ocean ──
  const oceanGeo = new THREE.PlaneGeometry(80, 50, 120, 80)
  oceanGeo.rotateX(-Math.PI / 2)
  oceanBase = new Float32Array(oceanGeo.attributes.position.array)
  const oceanMat = new THREE.MeshStandardMaterial({
    color: 0x1a4060,
    roughness: 0.2,
    metalness: 0.6,
    flatShading: false,
    transparent: true,
    opacity: 0.7,
  })
  oceanMesh = new THREE.Mesh(oceanGeo, oceanMat)
  oceanMesh.position.y = -0.5
  oceanMesh.receiveShadow = true
  scene.add(oceanMesh)

  // ── Terrain ──
  const terrainGroup = new THREE.Group()
  const terrainGeo = new THREE.PlaneGeometry(60, 35, 80, 60)
  terrainGeo.rotateX(-Math.PI / 2)
  const tPositions = terrainGeo.attributes.position
  for (let i = 0; i < tPositions.count; i++) {
    const x = tPositions.getX(i), z = tPositions.getY(i)
    let h = 0
    h += Math.sin(x * 0.25) * Math.cos(z * 0.3) * 1.2
    h += Math.cos(x * 0.5 + 1.2) * Math.sin(z * 0.45) * 0.6
    h += Math.sin(x * 0.8) * Math.cos(z * 0.7) * 0.3
    h += Math.cos(x * 1.3 + z * 0.9) * 0.2
    // Flatten near edges
    const distFromCenter = Math.sqrt(x * x + z * z) / 20
    h *= 1 - Math.max(0, (distFromCenter - 0.5) * 2)
    h = Math.max(0, h)
    tPositions.setZ(i, h)
  }
  terrainGeo.computeVertexNormals()
  const terrainMat = new THREE.MeshStandardMaterial({
    color: 0x2d4a2d,
    roughness: 0.85,
    metalness: 0.05,
    transparent: true,
    opacity: 0.75,
  })
  const terrain = new THREE.Mesh(terrainGeo, terrainMat)
  terrain.position.set(0, 0.02, -3)
  terrain.receiveShadow = true
  terrainGroup.add(terrain)

  // Near-terrain darker strip (coast)
  const coastGeo = new THREE.PlaneGeometry(60, 4, 60, 2)
  coastGeo.rotateX(-Math.PI / 2)
  const coastMat = new THREE.MeshStandardMaterial({
    color: 0x3d5a3d,
    roughness: 0.9,
    metalness: 0.02,
    transparent: true,
    opacity: 0.7,
  })
  const coast = new THREE.Mesh(coastGeo, coastMat)
  coast.position.set(0, 0.01, -1.5)
  coast.receiveShadow = true
  terrainGroup.add(coast)

  scene.add(terrainGroup)

  // ── Turbine positions ──
  const turbineLayout: Array<{ x: number; z: number; scale: number; rotY: number }> = [
    // Front row (large)
    { x: -9, z: 5, scale: 1.0, rotY: 0.3 },
    { x: -4, z: 6, scale: 1.05, rotY: -0.2 },
    { x: 2, z: 4.5, scale: 1.0, rotY: 0.1 },
    { x: 7, z: 5.5, scale: 0.95, rotY: -0.15 },
    // Middle row
    { x: -10, z: 0, scale: 0.75, rotY: 0.5 },
    { x: -5, z: 0.5, scale: 0.8, rotY: -0.3 },
    { x: 0, z: -0.5, scale: 0.78, rotY: 0.0 },
    { x: 5, z: 0, scale: 0.82, rotY: -0.4 },
    { x: 10, z: 0.5, scale: 0.72, rotY: 0.35 },
    // Back row (small)
    { x: -8, z: -4, scale: 0.5, rotY: -0.1 },
    { x: -3, z: -4.5, scale: 0.55, rotY: 0.25 },
    { x: 3, z: -4, scale: 0.52, rotY: -0.2 },
    { x: 8, z: -4.5, scale: 0.48, rotY: 0.15 },
  ]

  // ── Load GLB model + instantiate ──
  modelGroup = new THREE.Group()
  const loader = new GLTFLoader()

  // Fallback: procedural turbine if GLB fails
  const createFallbackTurbine = (): THREE.Group => {
    const g = new THREE.Group()
    // Tower
    const tower = new THREE.Mesh(
      new THREE.CylinderGeometry(0.15, 0.3, 4.5, 12),
      new THREE.MeshStandardMaterial({ color: 0xddeeff, roughness: 0.3, metalness: 0.7 })
    )
    tower.position.y = 2.25
    tower.castShadow = true
    g.add(tower)
    // Nacelle
    const nacelle = new THREE.Mesh(
      new THREE.BoxGeometry(0.6, 0.45, 1.2),
      new THREE.MeshStandardMaterial({ color: 0xeef2f6, roughness: 0.25, metalness: 0.6 })
    )
    nacelle.position.set(0, 4.7, 0.15)
    nacelle.castShadow = true
    const nacelleGroup = new THREE.Group()
    nacelleGroup.add(nacelle)
    // Blades
    const blades = new THREE.Group()
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2
      const b = new THREE.Mesh(
        new THREE.BoxGeometry(0.08, 1.8, 0.04),
        new THREE.MeshStandardMaterial({ color: 0xf5f7fa, roughness: 0.2, metalness: 0.5 })
      )
      b.position.set(Math.cos(a) * 0.8, Math.sin(a) * 0.8, 0)
      b.rotation.z = a
      b.castShadow = true
      blades.add(b)
    }
    blades.position.set(0, 4.7, 0.95)
    blades.name = 'blades'
    nacelleGroup.add(blades)
    nacelleGroup.position.set(0, 0, 0)
    nacelleGroup.name = 'nacelle'
    g.add(nacelleGroup)
    return g
  }

  try {
    const gltf = await loader.loadAsync('/wind_turbine.glb')
    const model = gltf.scene

    // Find blade/nacelle parts for animation
    model.traverse((child) => {
      const name = child.name.toLowerCase()
      if (
        name.includes('blade') || name.includes('rotor') ||
        name.includes('叶片') || name.includes('桨') ||
        name.includes('propeller') || name.includes('fan')
      ) {
        bladeGroups.push(child)
      }
    })

    // Clone for each position
    turbineLayout.forEach((pos) => {
      const clone = model.clone(true)
      clone.scale.setScalar(pos.scale * 0.012)
      clone.position.set(pos.x, 0, pos.z)
      clone.rotation.y = pos.rotY
      clone.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          child.castShadow = true
          child.receiveShadow = true
        }
        // Collect blade groups from clones
        const name = child.name.toLowerCase()
        if (
          name.includes('blade') || name.includes('rotor') ||
          name.includes('叶片') || name.includes('桨')
        ) {
          if (!bladeGroups.includes(child)) bladeGroups.push(child)
        }
      })
      modelGroup.add(clone)
    })

    // If no blade groups found by name, try to find by geometry
    if (bladeGroups.length === 0) {
      modelGroup.traverse((child) => {
        if (child instanceof THREE.Group && child.children.length >= 3) {
          const allMeshes = child.children.every(
            c => (c as THREE.Mesh).isMesh && c.position.length() > 0.3
          )
          if (allMeshes && child.children.length <= 5) {
            bladeGroups.push(child)
          }
        }
      })
    }
  } catch {
    // Use fallback procedural turbines
    turbineLayout.forEach((pos) => {
      const t = createFallbackTurbine()
      t.scale.setScalar(pos.scale)
      t.position.set(pos.x, 0, pos.z)
      t.rotation.y = pos.rotY
      // Find blades for animation
      t.traverse((child) => {
        if (child.name === 'blades') bladeGroups.push(child)
      })
      modelGroup.add(t)
    })
  }

  scene.add(modelGroup)

  // ── Post Processing ──
  const renderPass = new RenderPass(scene, camera)
  renderPass.clearAlpha = 0
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.35,   // strength (降低让效果图更明显)
    0.4,   // radius
    0.85,  // threshold
  )
  composer = new EffectComposer(renderer)
  composer.addPass(renderPass)
  composer.addPass(bloomPass)

  // ── Animate ──
  clock = new THREE.Clock()
  function animate() {
    animId = requestAnimationFrame(animate)
    const dt = Math.min(clock.getDelta(), 0.1)
    const elapsed = clock.elapsedTime

    // Ocean waves
    const pos = oceanMesh.geometry.attributes.position
    if (pos && oceanBase.length > 0) {
      const cnt = Math.min(pos.count, oceanBase.length / 3)
      for (let i = 0; i < cnt; i++) {
        const ox = oceanBase[i * 3]
        const oz = oceanBase[i * 3 + 2]
        const wave = Math.sin(ox * 0.35 + elapsed * 0.8) * 0.18 +
                     Math.cos(oz * 0.4 + elapsed * 0.6) * 0.15 +
                     Math.sin((ox + oz) * 0.5 + elapsed * 1.1) * 0.1
        pos.setZ(i, wave)
      }
      pos.needsUpdate = true
    }

    // Rotate blades
    const bladeSpeed = 0.6
    bladeGroups.forEach(b => {
      b.rotation.z += bladeSpeed * dt
    })

    // Update sky uniform
    if (skyMat.uniforms) {
      skyMat.uniforms.uTime.value = elapsed
    }

    controls.update()
    composer.render()
  }
  animate()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  controls?.dispose()
  renderer?.dispose()
  scene?.clear()
})

function onResize() {
  if (!renderer || !camera || !composer) return
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
  composer.setSize(window.innerWidth, window.innerHeight)
}
window.addEventListener('resize', onResize)
</script>

<template>
  <canvas ref="canvasRef" class="wind-farm-canvas"></canvas>
</template>

<style scoped>
.wind-farm-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
}
</style>
