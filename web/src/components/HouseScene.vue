<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'

const canvasHost = ref(null)
let renderer
let animationFrame
let cleanupResize

onMounted(() => {
  const host = canvasHost.value
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#eef2ef')

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100)
  camera.position.set(5.2, 4.1, 6.4)
  camera.lookAt(0, 1.1, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  host.appendChild(renderer.domElement)

  const ambient = new THREE.HemisphereLight('#ffffff', '#a8b7b0', 2.4)
  const keyLight = new THREE.DirectionalLight('#fff7df', 2.6)
  keyLight.position.set(4, 7, 5)
  scene.add(ambient, keyLight)

  const base = new THREE.Mesh(
    new THREE.CylinderGeometry(2.55, 2.8, 0.3, 4),
    new THREE.MeshStandardMaterial({ color: '#d8dfda', roughness: 0.95 }),
  )
  base.rotation.y = Math.PI / 4
  base.position.y = -0.18
  scene.add(base)

  const building = new THREE.Group()
  const shell = new THREE.MeshStandardMaterial({ color: '#e8e4dc', roughness: 0.83 })
  const windowMaterial = new THREE.MeshStandardMaterial({ color: '#477f83', emissive: '#245459', emissiveIntensity: 0.23, roughness: 0.35 })
  const roofMaterial = new THREE.MeshStandardMaterial({ color: '#d66f47', roughness: 0.72 })
  const floor = new THREE.BoxGeometry(3.2, 0.72, 2.7)

  for (let level = 0; level < 3; level += 1) {
    const block = new THREE.Mesh(floor, shell)
    block.position.y = level * 0.78 + 0.42
    building.add(block)
    for (let column = -1; column <= 1; column += 1) {
      const window = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.35, 0.04), windowMaterial)
      window.position.set(column * 0.92, level * 0.78 + 0.45, 1.37)
      building.add(window)
    }
  }

  const roof = new THREE.Mesh(new THREE.ConeGeometry(2.45, 1.18, 4), roofMaterial)
  roof.position.y = 3.12
  roof.rotation.y = Math.PI / 4
  building.add(roof)
  scene.add(building)

  const resize = () => {
    const { width, height } = host.getBoundingClientRect()
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
  }
  resize()
  const observer = new ResizeObserver(resize)
  observer.observe(host)
  cleanupResize = () => observer.disconnect()

  const render = () => {
    building.rotation.y += 0.0024
    renderer.render(scene, camera)
    animationFrame = requestAnimationFrame(render)
  }
  render()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationFrame)
  cleanupResize?.()
  renderer?.dispose()
})
</script>

<template>
  <div ref="canvasHost" class="house-scene" aria-label="房源三维概览" />
</template>
