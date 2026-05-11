'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const PARTICLE_COUNT = 300

export default function L0FarMist() {
  const meshRef = useRef<THREE.Points>(null)
  const speedsRef = useRef<Float32Array>(new Float32Array(PARTICLE_COUNT))

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(PARTICLE_COUNT * 3)
    const sz = new Float32Array(PARTICLE_COUNT)
    const al = new Float32Array(PARTICLE_COUNT)

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const isFar = Math.random() < 0.6
      pos[i * 3] = (Math.random() - 0.5) * 20
      pos[i * 3 + 1] = (Math.random() - 0.5) * 14
      pos[i * 3 + 2] = isFar ? -6 + Math.random() * 3 : -4 + Math.random() * 3
      sz[i] = isFar ? 8 + Math.random() * 6 : 3 + Math.random() * 4
      al[i] = isFar ? 0.2 + Math.random() * 0.15 : 0.35 + Math.random() * 0.2
      speedsRef.current[i] = (0.0005 + Math.random() * 0.001) * (isFar ? 0.5 : 1.5)
    }

    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('aSize', new THREE.BufferAttribute(sz, 1))
    geo.setAttribute('aAlpha', new THREE.BufferAttribute(al, 1))
    return geo
  }, [])

  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: {
        uColor: { value: new THREE.Color('#c8c0b0') },
        uPixelRatio: { value: typeof window !== 'undefined' ? Math.min(window.devicePixelRatio, 2) : 1 },
      },
      vertexShader: `
        attribute float aSize;
        attribute float aAlpha;
        varying float vAlpha;
        uniform float uPixelRatio;
        void main() {
          vAlpha = aAlpha;
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * uPixelRatio * (100.0 / -mvPosition.z);
          gl_PointSize = max(gl_PointSize, 1.0);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        varying float vAlpha;
        void main() {
          float d = length(gl_PointCoord - vec2(0.5));
          if (d > 0.5) discard;
          float a = vAlpha * smoothstep(0.5, 0.0, d);
          gl_FragColor = vec4(uColor, a);
        }
      `,
    })
  }, [])

  useFrame(() => {
    if (!meshRef.current) return
    const posAttr = meshRef.current.geometry.attributes.position
    const arr = posAttr.array as Float32Array
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const speed = speedsRef.current[i]
      arr[i * 3] += Math.sin(Date.now() * speed + i) * 0.001
      arr[i * 3 + 1] += Math.cos(Date.now() * speed * 0.7 + i) * 0.001
    }
    posAttr.needsUpdate = true
  })

  return <points ref={meshRef} geometry={geometry} material={material} />
}
