<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animId = 0
let renderer: THREE.WebGLRenderer | null = null

function createBladeShape(length: number, width: number): THREE.Shape {
  const shape = new THREE.Shape()
  shape.moveTo(0, -width * 0.15)
  shape.bezierCurveTo(length * 0.3, -width * 0.05, length * 0.7, width * 0.02, length, 0)
  shape.bezierCurveTo(length * 0.7, -width * 0.02, length * 0.3, width * 0.05, 0, width * 0.15)
  return shape
}

function createTurbine(height: number): THREE.Group {
  const g = new THREE.Group()

  // Tapered tower
  const towerGeo = new THREE.CylinderGeometry(0.12, 0.3, height, 12)
  const towerMat = new THREE.MeshStandardMaterial({ color: 0xdddddd, roughness: 0.6, metalness: 0.3 })
  const tower = new THREE.Mesh(towerGeo, towerMat)
  tower.position.y = height / 2
  tower.castShadow = true
  g.add(tower)

  // Platform
  const platGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.15, 12)
  const plat = new THREE.Mesh(platGeo, towerMat)
  plat.position.y = height
  g.add(plat)

  // Nacelle
  const nacelleGroup = new THREE.Group()
  const bodyGeo = new THREE.BoxGeometry(0.5, 0.45, 1.2)
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshStandardMaterial({ color: 0xe8e8e8, roughness: 0.5, metalness: 0.4 }))
  nacelleGroup.add(body)

  // Nacelle rear dome
  const domeGeo = new THREE.SphereGeometry(0.25, 8, 8, 0, Math.PI * 2, 0, Math.PI / 2)
  const dome = new THREE.Mesh(domeGeo, new THREE.MeshStandardMaterial({ color: 0xd0d0d0, roughness: 0.5, metalness: 0.3 }))
  dome.position.z = -0.6
  nacelleGroup.add(dome)

  const spinnerGeo = new THREE.ConeGeometry(0.22, 0.5, 12)
  const spinner = new THREE.Mesh(spinnerGeo, new THREE.MeshStandardMaterial({ color: 0xcc0000, roughness: 0.3, metalness: 0.2 }))
  spinner.rotation.x = -Math.PI / 2
  spinner.position.z = 0.7
  nacelleGroup.add(spinner)

  nacelleGroup.position.y = height + 0.2
  g.add(nacelleGroup)

  // Blades
  const bladeGroup = new THREE.Group()
  const bladeShape = createBladeShape(1.5, 0.2)
  const extrudeSettings: THREE.ExtrudeGeometryOptions = { steps: 1, depth: 0.04, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.01, bevelSegments: 3 }
  const bladeGeoTemplate = new THREE.ExtrudeGeometry(bladeShape, extrudeSettings)
  const bladeMat = new THREE.MeshStandardMaterial({ color: 0xf5f5f5, roughness: 0.4, metalness: 0.1 })

  for (let i = 0; i < 3; i++) {
    const angle = (i / 3) * Math.PI * 2
    const blade = new THREE.Mesh(bladeGeoTemplate.clone(), bladeMat)
    blade.position.y = Math.sin(angle) * 0.05
    blade.position.x = Math.cos(angle) * 0.05
    blade.rotation.set(0, 0, angle)
    blade.castShadow = true
    bladeGroup.add(blade)
  }
  bladeGroup.position.set(0, height + 0.2, 0.8)
  bladeGroup.name = 'blades'
  g.add(bladeGroup)

  return g
}

onMounted(() => {
  if (!canvasRef.value) return
  const w = window.innerWidth, h = window.innerHeight

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1628)
  scene.fog = new THREE.Fog(0x0a1628, 30, 80)

  const camera = new THREE.PerspectiveCamera(50, w / h, 0.5, 150)
  camera.position.set(5, 10, 28)
  camera.lookAt(0, 4, 0)

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0

  // Lighting
  const ambient = new THREE.AmbientLight(0x334466, 0.6)
  scene.add(ambient)
  const moon = new THREE.DirectionalLight(0xccddff, 2.5)
  moon.position.set(30, 25, -10)
  moon.castShadow = true
  moon.shadow.mapSize.set(2048, 2048)
  moon.shadow.camera.near = 0.5; moon.shadow.camera.far = 100
  moon.shadow.camera.left = -30; moon.shadow.camera.right = 30
  moon.shadow.camera.top = 20; moon.shadow.camera.bottom = -20
  scene.add(moon)
  const rim = new THREE.DirectionalLight(0x4488cc, 1.0)
  rim.position.set(-15, 5, 20)
  scene.add(rim)

  // Ocean
  const oceanGeo = new THREE.PlaneGeometry(80, 60, 80, 80)
  const oceanMat = new THREE.MeshStandardMaterial({
    color: 0x0c2d50, roughness: 0.3, metalness: 0.6,
    flatShading: false,
  })
  const ocean = new THREE.Mesh(oceanGeo, oceanMat)
  ocean.rotation.x = -Math.PI / 2
  ocean.position.y = -0.2
  ocean.receiveShadow = true
  ocean.name = 'ocean'
  scene.add(ocean)

  // Turbines
  const turbineGroup: THREE.Group[] = []
  // Row 1 (closer)
  ;[[-10, 6], [-5, 7], [0, 5], [5, 8], [10, 6]].forEach(([x, z]) => {
    const t = createTurbine(4 + Math.random() * 1)
    t.position.set(x, 0, z)
    t.rotation.y = (Math.random() - 0.5) * 0.2
    scene.add(t)
    turbineGroup.push(t)
  })
  // Row 2 (mid)
  ;[[-12, -2], [-7, 0], [-2, -1], [4, 2], [9, 0]].forEach(([x, z]) => {
    const t = createTurbine(3.5 + Math.random() * 1)
    t.position.set(x, 0, z)
    t.rotation.y = (Math.random() - 0.5) * 0.2
    scene.add(t)
    turbineGroup.push(t)
  })
  // Row 3 (far, smaller)
  ;[[-14, -8], [-8, -10], [0, -9], [6, -11], [12, -7]].forEach(([x, z]) => {
    const t = createTurbine(2.5 + Math.random() * 0.8)
    t.scale.setScalar(0.6)
    t.position.set(x, 0, z - 2)
    t.rotation.y = (Math.random() - 0.5) * 0.2
    scene.add(t)
    turbineGroup.push(t)
  })

  // Distant stars
  const starsGeo = new THREE.BufferGeometry()
  const starPositions = new Float32Array(400 * 3)
  for (let i = 0; i < starPositions.length; i += 3) {
    starPositions[i] = (Math.random() - 0.5) * 70
    starPositions[i + 1] = 8 + Math.random() * 25
    starPositions[i + 2] = -5 + Math.random() * 15
  }
  starsGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3))
  scene.add(new THREE.Points(starsGeo, new THREE.PointsMaterial({
    color: 0xcceeff, size: 0.06, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending,
  })))

  // Wave lighting highlights on ocean surface
  const clock = new THREE.Clock()
  const origOceanPositions = new Float32Array((ocean.geometry as THREE.BufferGeometry).attributes.position.array)

  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    // Animate ocean
    const pos = (ocean.geometry as THREE.BufferGeometry).attributes.position
    if (pos) {
      for (let i = 0; i < Math.min(pos.count, origOceanPositions.length / 3); i++) {
        const ox = origOceanPositions[i * 3]
        const oy = origOceanPositions[i * 3 + 1]
        pos.setZ(i, Math.sin(ox * 0.4 + t * 1.0) * 0.15 + Math.cos(oy * 0.5 + t * 0.7) * 0.12)
      }
      pos.needsUpdate = true
    }

    // Rotate blades
    turbineGroup.forEach(tg => {
      const b = tg.getObjectByName('blades')
      if (b) b.rotation.z += 0.01 + Math.random() * 0.003
    })

    camera.position.x = Math.sin(t * 0.03) * 1.5
    camera.position.z = 28 + Math.cos(t * 0.04) * 1
    camera.lookAt(0, 3, -5)

    renderer!.render(scene, camera)
  }
  animate()

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer!.setSize(window.innerWidth, window.innerHeight)
  })
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  renderer?.dispose()
})
</script>

<template>
  <canvas ref="canvasRef" class="wind-bg"></canvas>
</template>

<style scoped>
.wind-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }
</style>
