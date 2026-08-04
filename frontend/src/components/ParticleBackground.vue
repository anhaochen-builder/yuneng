<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer
let particles: THREE.Points, animId: number
const mouse = new THREE.Vector2()

onMounted(() => {
  if (!canvasRef.value) return
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
  camera.position.z = 30
  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, alpha: true, antialias: true })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  const count = window.innerWidth > 1400 ? 300 : 150
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count * 3; i += 3) {
    positions[i] = (Math.random() - 0.5) * 80
    positions[i + 1] = (Math.random() - 0.5) * 50
    positions[i + 2] = (Math.random() - 0.5) * 20
  }
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const material = new THREE.PointsMaterial({ color: 0x00f0ff, size: 0.15, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending })
  particles = new THREE.Points(geometry, material)
  scene.add(particles)

  window.addEventListener('mousemove', e => { mouse.x = (e.clientX / window.innerWidth) * 2 - 1; mouse.y = -(e.clientY / window.innerHeight) * 2 + 1 })

  function animate() {
    animId = requestAnimationFrame(animate)
    particles.rotation.y += 0.0003
    particles.rotation.x += 0.0001
    particles.position.x += mouse.x * 0.02
    particles.position.y += mouse.y * 0.02
    renderer.render(scene, camera)
  }
  animate()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  renderer?.dispose()
})
</script>

<template>
  <canvas ref="canvasRef" class="particle-bg"></canvas>
</template>

<style scoped>
.particle-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }
</style>
