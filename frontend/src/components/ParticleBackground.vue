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
  scene.fog = new THREE.Fog(0x0a1628, 25, 80)

  const camera = new THREE.PerspectiveCamera(45, w / h, 0.5, 150)
  camera.position.set(0, 10, 32)
  camera.lookAt(0, 3, -5)

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0

  scene.add(new THREE.AmbientLight(0x334466, 0.5))

  const moon = new THREE.DirectionalLight(0xccddff, 2.8)
  moon.position.set(25, 22, -8)
  moon.castShadow = true
  moon.shadow.mapSize.set(2048, 2048)
  moon.shadow.camera.near = 0.5; moon.shadow.camera.far = 100
  moon.shadow.camera.left = -35; moon.shadow.camera.right = 35
  moon.shadow.camera.top = 25; moon.shadow.camera.bottom = -25
  scene.add(moon)

  scene.add(new THREE.DirectionalLight(0x4488cc, 0.8).translateX(-12).translateY(5).translateZ(18) as any)

  // Ocean
  const oceanGeo = new THREE.PlaneGeometry(90, 60, 100, 100)
  const ocean = new THREE.Mesh(oceanGeo, new THREE.MeshStandardMaterial({ color: 0x0c2d50, roughness: 0.25, metalness: 0.7 }))
  ocean.rotation.x = -Math.PI / 2
  ocean.position.y = -0.3
  ocean.receiveShadow = true
  ocean.name = 'ocean'
  scene.add(ocean)
  const posAttr = oceanGeo.attributes.position
  const origOceanPos = new Float32Array(posAttr ? posAttr.array : new Float32Array())

  // Stars
  const starsGeo = new THREE.BufferGeometry()
  const starsPos = new Float32Array(500 * 3)
  for (let i = 0; i < starsPos.length; i += 3) {
    starsPos[i] = (Math.random() - 0.5) * 70
    starsPos[i + 1] = 10 + Math.random() * 25
    starsPos[i + 2] = -5 + Math.random() * 12
  }
  starsGeo.setAttribute('position', new THREE.BufferAttribute(starsPos, 3))
  scene.add(new THREE.Points(starsGeo, new THREE.PointsMaterial({ color: 0xcceeff, size: 0.06, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending })))

  // Load NASA wind turbine model
  const loader = new GLTFLoader()
  const bladeGroups: THREE.Object3D[] = []

  loader.load('/wind_turbine.glb', (gltf) => {
    const model = gltf.scene

    const positions: Array<[number, number]> = [
      [-10, 6], [-5, 7], [0, 5], [5, 8], [10, 6],
      [-12, -2], [-7, 0], [-2, -1], [4, 2], [9, 0],
      [-14, -7], [-8, -8], [0, -7], [6, -9], [12, -6],
    ]

    positions.forEach(([x, z], i) => {
      const turbine = model.clone()
      const scale = i < 5 ? 0.022 : i < 10 ? 0.016 : 0.011
      turbine.scale.setScalar(scale)
      turbine.position.set(x, 0, z)
      turbine.rotation.y = Math.random() * Math.PI * 2
      turbine.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          child.castShadow = true
          child.receiveShadow = true
        }
      })
      scene.add(turbine)

      turbine.traverse((child) => {
        const name = child.name.toLowerCase()
        if (name.includes('blade') || name.includes('rotor') || name.includes('hub') || name.includes('prop')) {
          const b = child.clone()
          b.name = 'blade'
          bladeGroups.push(b)
        }
      })
    })
  })

  const clock = new THREE.Clock()
  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    const posAttr = (ocean.geometry as THREE.BufferGeometry).attributes.position
    if (posAttr) {
      for (let i = 0; i < Math.min(posAttr.count, origOceanPos.length / 3); i++) {
        const ox = origOceanPos[i * 3] as number, oy = origOceanPos[i * 3 + 1] as number
        posAttr.setZ(i, Math.sin(ox * 0.4 + t * 1.0) * 0.12 + Math.cos(oy * 0.5 + t * 0.7) * 0.1)
      }
      posAttr.needsUpdate = true
    }

    bladeGroups.forEach(b => { b.rotation.y += 0.005 })

    camera.position.x = Math.sin(t * 0.03) * 1.5
    camera.position.z = 32 + Math.cos(t * 0.04) * 1.5
    camera.lookAt(0, 2, -5)

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
