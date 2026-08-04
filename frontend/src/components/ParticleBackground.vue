<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animId = 0
let renderer: THREE.WebGLRenderer | null = null

onMounted(() => {
  if (!canvasRef.value) return
  const w = window.innerWidth, h = window.innerHeight

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1628)
  scene.fog = new THREE.FogExp2(0x0a1628, 0.00008)

  const camera = new THREE.PerspectiveCamera(50, w / h, 1, 200)
  camera.position.set(0, 8, 22)
  camera.lookAt(0, 3, -3)

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.2
  renderer.setClearColor(0x0a1628)

  scene.add(new THREE.AmbientLight(0x446688, 0.7))

  const moon = new THREE.DirectionalLight(0xccddff, 3.5)
  moon.position.set(20, 18, -5)
  moon.castShadow = true
  moon.shadow.mapSize.set(1024, 1024)
  moon.shadow.camera.near = 1; moon.shadow.camera.far = 80
  moon.shadow.camera.left = -30; moon.shadow.camera.right = 30
  moon.shadow.camera.top = 20; moon.shadow.camera.bottom = -20
  scene.add(moon)

  scene.add(new THREE.HemisphereLight(0x446688, 0x1a2a3a, 0.4))

  // Ocean with visible base color
  const oceanGeo = new THREE.PlaneGeometry(100, 60, 80, 80)
  const ocean = new THREE.Mesh(oceanGeo, new THREE.MeshPhongMaterial({
    color: 0x1a3050, specular: 0x335577, shininess: 30, flatShading: true,
  }))
  ocean.rotation.x = -Math.PI / 2
  ocean.position.y = -0.5
  ocean.receiveShadow = true
  scene.add(ocean)
  const origOceanPos = new Float32Array(oceanGeo.attributes.position.array)

  // Load model
  const loader = new GLTFLoader()
  const bladeGroups: THREE.Object3D[] = []

  loader.load('/wind_turbine.glb',
    (gltf) => {
      const model = gltf.scene

      const positions: Array<[number, number]> = [
        [-9, 8], [-4, 10], [1, 7], [6, 9], [11, 6],
        [-11, -1], [-6, 1], [-1, 0], [5, 3], [10, 1],
        [-13, -7], [-7, -8], [0, -6], [7, -8], [13, -5],
      ]

      positions.forEach(([x, z], i) => {
        const turbine = model.clone()
        const scale = i < 5 ? 0.025 : i < 10 ? 0.018 : 0.012
        turbine.scale.setScalar(scale)
        turbine.position.set(x, 0, z)
        turbine.rotation.y = Math.random() * Math.PI * 2
        turbine.traverse((child: any) => {
          if (child.isMesh) {
            child.castShadow = true
            child.receiveShadow = true
          }
        })
        scene.add(turbine)

        // Collect blade parts for animation
        turbine.traverse((child: any) => {
          const n = (child.name || '').toLowerCase()
          if (n.includes('blade') || n.includes('rotor') || n.includes('hub') || n.includes('hub_1') || n.includes('propeller')) {
            child.name = 'blade_part'
            bladeGroups.push(child as THREE.Object3D)
          }
        })
      })
    },
    (progress) => {
      if (progress.total > 0) {
        const pct = Math.round((progress.loaded / progress.total) * 100)
      }
    },
    (err) => { console.warn('3D风机模型加载失败，使用降级背景:', err) }
  )

  const clock = new THREE.Clock()
  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    const posAttr = (ocean.geometry as THREE.BufferGeometry).attributes.position
    if (posAttr && origOceanPos.length > 0) {
      for (let i = 0; i < Math.min(posAttr.count, origOceanPos.length / 3); i++) {
        const ox = origOceanPos[i * 3] as number, oy = origOceanPos[i * 3 + 1] as number
        posAttr.setZ(i, Math.sin(ox * 0.3 + t) * 0.15 + Math.cos(oy * 0.4 + t * 0.8) * 0.12)
      }
      posAttr.needsUpdate = true
    }

    bladeGroups.forEach(b => { if (b) b.rotation.z += 0.007 })

    camera.position.x = Math.sin(t * 0.04) * 2
    camera.position.z = 22 + Math.cos(t * 0.05) * 2
    camera.lookAt(0, 2.5, -3)

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
.wind-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; display: block; }
</style>
