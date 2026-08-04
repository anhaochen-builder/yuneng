<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animId = 0
let renderer: THREE.WebGLRenderer | null = null

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(window.innerWidth, window.innerHeight)

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1628)
  scene.fog = new THREE.Fog(0x0a1628, 20, 80)

  const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 1, 200)
  camera.position.set(0, 10, 25)
  camera.lookAt(0, 3, -5)

  // Ocean
  const oceanGeo = new THREE.PlaneGeometry(120, 60, 100, 100)
  const ocean = new THREE.Mesh(oceanGeo, new THREE.MeshPhongMaterial({
    color: 0x1a3050, specular: 0x336699, shininess: 30, flatShading: true,
  }))
  ocean.rotation.x = -Math.PI / 2
  ocean.position.y = -1
  scene.add(ocean)

  scene.add(new THREE.AmbientLight(0x446688, 0.8))
  const sun = new THREE.DirectionalLight(0xccddff, 2.0)
  sun.position.set(15, 18, 5)
  scene.add(sun)

  // Procedural turbines (visible even without GLB)
  const createProceduralTurbine = (): THREE.Group => {
    const g = new THREE.Group()
    g.add(new THREE.Mesh(
      new THREE.CylinderGeometry(0.12, 0.28, 4, 8),
      new THREE.MeshPhongMaterial({ color: 0xddeeff, specular: 0x334455, shininess: 20 })
    ).translateY(2) as THREE.Mesh)
    g.add(new THREE.Mesh(
      new THREE.BoxGeometry(0.5, 0.4, 1.1),
      new THREE.MeshPhongMaterial({ color: 0xeef0f2, specular: 0x445566, shininess: 25 })
    ).translateY(4.4).translateZ(0.1) as THREE.Mesh)
    const hub = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 8, 8),
      new THREE.MeshPhongMaterial({ color: 0x778899 })
    )
    hub.position.set(0, 4.4, 0.7)
    g.add(hub)
    const blades = new THREE.Group()
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2
      const b = new THREE.Mesh(
        new THREE.BoxGeometry(0.07, 1.5, 0.04),
        new THREE.MeshPhongMaterial({ color: 0xf0f2f5 })
      )
      b.position.set(Math.cos(a) * 0.7, Math.sin(a) * 0.7, 0.01)
      b.rotation.z = a
      blades.add(b)
    }
    blades.position.set(0, 4.4, 0.85)
    blades.name = 'blades'
    g.add(blades)
    return g
  }

  const bladeGroups: THREE.Group[] = []
  const turbs: Array<[number, number]> = [
    [-10,6],[-5,7],[0,5],[5,8],[10,6],
    [-12,-2],[-7,0],[-2,-1],[4,2],[9,0],
    [-14,-7],[-8,-8],[0,-7],[6,-9],[12,-6],
  ]
  turbs.forEach(([x, z], i) => {
    const t = createProceduralTurbine()
    t.scale.setScalar(i < 5 ? 1.0 : i < 10 ? 0.7 : 0.5)
    t.position.set(x, 0, z)
    t.rotation.y = Math.random() * Math.PI * 2
    scene.add(t)
    const b = t.getObjectByName('blades')
    if (b) bladeGroups.push(b as THREE.Group)
  })

  // Stars
  const starsGeo = new THREE.BufferGeometry()
  const arr = new Float32Array(400 * 3)
  for (let i = 0; i < arr.length; i += 3) {
    arr[i] = (Math.random() - 0.5) * 80
    arr[i + 1] = 10 + Math.random() * 25
    arr[i + 2] = -5 + Math.random() * 12
  }
  starsGeo.setAttribute('position', new THREE.BufferAttribute(arr, 3))
  scene.add(new THREE.Points(starsGeo, new THREE.PointsMaterial({ color: 0xcceeff, size: 0.06, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending })))

  const oceanArr = new Float32Array(oceanGeo.attributes.position.array)
  const clock = new THREE.Clock()

  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    const pos = (ocean.geometry as THREE.BufferGeometry).attributes.position
    if (pos && oceanArr.length > 0) {
      const cnt = Math.min(pos.count, oceanArr.length / 3)
      for (let i = 0; i < cnt; i++) {
        pos.setZ(i, Math.sin(oceanArr[i * 3] * 0.3 + t) * 0.15 + Math.cos(oceanArr[i * 3 + 1] * 0.4 + t * 0.8) * 0.12)
      }
      pos.needsUpdate = true
    }

    bladeGroups.forEach(b => { if (b) b.rotation.z += 0.008 })

    camera.position.x = Math.sin(t * 0.03) * 1.5
    camera.position.z = 25 + Math.cos(t * 0.04) * 1.5
    camera.lookAt(0, 2, -5)

    renderer!.render(scene, camera)
  }
  animate()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  renderer?.dispose()
})

function onResize() {
  // handled by canvas CSS 100% size, Three.js renderer resized in mount
}
window.addEventListener('resize', () => {
  if (renderer) renderer.setSize(window.innerWidth, window.innerHeight)
})
</script>

<template>
  <canvas ref="canvasRef" class="wind-bg"></canvas>
</template>

<style scoped>
.wind-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; }
</style>
