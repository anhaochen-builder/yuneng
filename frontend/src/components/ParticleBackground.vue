<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animId: number
let renderer: THREE.WebGLRenderer

function createTurbine(x: number, z: number, scale: number): THREE.Group {
  const group = new THREE.Group()

  const towerGeo = new THREE.CylinderGeometry(0.15, 0.25, 4 * scale, 8)
  const towerMat = new THREE.MeshPhongMaterial({ color: 0x8899aa, emissive: 0x112233, emissiveIntensity: 0.3 })
  const tower = new THREE.Mesh(towerGeo, towerMat)
  tower.position.y = 2 * scale
  group.add(tower)

  const nacelleGeo = new THREE.BoxGeometry(0.6 * scale, 0.3 * scale, 1.2 * scale)
  const nacelleMat = new THREE.MeshPhongMaterial({ color: 0xaabbcc, emissive: 0x111122, emissiveIntensity: 0.3 })
  const nacelle = new THREE.Mesh(nacelleGeo, nacelleMat)
  nacelle.position.y = 4.3 * scale
  nacelle.position.z = 0.1 * scale
  group.add(nacelle)

  const hubGeo = new THREE.SphereGeometry(0.22 * scale, 8, 8)
  const hubMat = new THREE.MeshPhongMaterial({ color: 0x667788 })
  const hub = new THREE.Mesh(hubGeo, hubMat)
  hub.position.y = 4.3 * scale
  hub.position.z = 0.6 * scale
  group.add(hub)

  const blades = new THREE.Group()
  for (let i = 0; i < 3; i++) {
    const angle = (i / 3) * Math.PI * 2
    const bladeGeo = new THREE.BoxGeometry(0.08 * scale, 1.6 * scale, 0.04 * scale)
    const bladeMat = new THREE.MeshPhongMaterial({ color: 0xeeeeff, emissive: 0x111122, emissiveIntensity: 0.2 })
    const blade = new THREE.Mesh(bladeGeo, bladeMat)
    blade.position.y = Math.sin(angle) * 0.8 * scale
    blade.position.x = Math.cos(angle) * 0.8 * scale
    blade.rotation.z = angle
    blades.add(blade)
  }
  blades.position.set(0, 4.3 * scale, 0.8 * scale)
  blades.name = 'blades'
  group.add(blades)

  group.position.set(x, 0, z)
  group.scale.setScalar(scale)
  return group
}

onMounted(() => {
  if (!canvasRef.value) return
  const w = window.innerWidth, h = window.innerHeight

  const scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x020b1a, 0.00015)
  scene.background = new THREE.Color(0x020b1a)

  const camera = new THREE.PerspectiveCamera(55, w / h, 0.5, 200)
  camera.position.set(0, 12, 22)
  camera.lookAt(0, 3, 0)

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, alpha: false, antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true

  const ambientLight = new THREE.AmbientLight(0x334466, 0.8)
  scene.add(ambientLight)
  const moonLight = new THREE.DirectionalLight(0x8899cc, 1.2)
  moonLight.position.set(20, 25, 10)
  scene.add(moonLight)
  const horizonLight = new THREE.PointLight(0x335577, 2, 60)
  horizonLight.position.set(0, 2, 15)
  scene.add(horizonLight)

  // Ocean
  const oceanGeo = new THREE.PlaneGeometry(80, 80, 60, 60)
  const oceanMat = new THREE.MeshPhongMaterial({
    color: 0x0a1f3a,
    emissive: 0x031018,
    emissiveIntensity: 0.6,
    shininess: 20,
    specular: 0x335577,
    flatShading: true,
  })
  const ocean = new THREE.Mesh(oceanGeo, oceanMat)
  ocean.rotation.x = -Math.PI / 2
  ocean.position.y = -0.5
  ocean.name = 'ocean'
  scene.add(ocean)

  // Grid of turbines
  const turbines: THREE.Group[] = []
  const positions = [
    [-8, 5], [-3, 8], [2, 4], [7, 7], [-6, -2], [0, -4], [5, -1], [9, 3], [-10, -6], [4, -7],
    [-12, 2], [11, -4], [-5, 10], [8, -8], [-2, -9],
  ]
  positions.forEach(([x, z]) => {
    const t = createTurbine(x as number, z as number, 0.7 + Math.random() * 0.5)
    turbines.push(t)
    scene.add(t)
  })

  // Stars
  const starsGeo = new THREE.BufferGeometry()
  const starsPos = new Float32Array(600 * 3)
  for (let i = 0; i < starsPos.length; i += 3) {
    starsPos[i] = (Math.random() - 0.5) * 80
    starsPos[i + 1] = 6 + Math.random() * 30
    starsPos[i + 2] = (Math.random() - 0.5) * 40
  }
  starsGeo.setAttribute('position', new THREE.BufferAttribute(starsPos, 3))
  const starsMat = new THREE.PointsMaterial({ color: 0xaaccee, size: 0.08, transparent: true, opacity: 0.6 })
  scene.add(new THREE.Points(starsGeo, starsMat))

  const clock = new THREE.Clock()
  function animate() {
    animId = requestAnimationFrame(animate)
    const t = clock.getElapsedTime()

    // Animate ocean waves
    const oceanGeo = (ocean.geometry as THREE.BufferGeometry)
    const pos = oceanGeo.attributes.position
    if (pos) {
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i)
        pos.setZ(i, Math.sin(x * 0.5 + t * 1.2) * 0.2 + Math.cos(y * 0.6 + t * 0.8) * 0.15)
      }
      pos.needsUpdate = true
    }

    // Rotate turbine blades
    turbines.forEach(tg => {
      const blades = tg.getObjectByName('blades')
      if (blades) blades.rotation.z += 0.008
    })

    // Subtle camera sway
    camera.position.x = Math.sin(t * 0.05) * 0.5
    camera.lookAt(Math.sin(t * 0.05) * 0.3, 3, 0)

    renderer.render(scene, camera)
  }
  animate()

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
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
