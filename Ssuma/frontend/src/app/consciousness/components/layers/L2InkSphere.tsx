'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function fibonacciSphere(count: number, radius: number): Float32Array {
  const positions = new Float32Array(count * 3)
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2
    const radiusAtY = Math.sqrt(1 - y * y)
    const theta = goldenAngle * i
    positions[i * 3] = Math.cos(theta) * radiusAtY * radius
    positions[i * 3 + 1] = y * radius
    positions[i * 3 + 2] = Math.sin(theta) * radiusAtY * radius
  }
  return positions
}

interface Props {
  voiceAmplitude?: number
  gradeColor?: string
}

export default function L2InkSphere({ voiceAmplitude = 0, gradeColor }: Props) {
  const meshRef = useRef<THREE.Points>(null)
  const timeRef = useRef(0)

  const particleCount = 500
  const basePositions = useMemo(() => fibonacciSphere(particleCount, 2), [])
  const currentPositions = useMemo(() => new Float32Array(basePositions), [basePositions])

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(currentPositions, 3))
    return geo
  }, [currentPositions])

  const material = useMemo(() => {
    return new THREE.PointsMaterial({
      color: new THREE.Color(gradeColor || '#6a9c79'),
      size: 0.08,
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
      sizeAttenuation: true,
    })
  }, [gradeColor])

  useFrame((_, delta) => {
    timeRef.current += delta
    if (!meshRef.current) return
    const posAttr = meshRef.current.geometry.attributes.position
    const arr = posAttr.array as Float32Array

    const pulseScale = 1 + voiceAmplitude * 0.2
    const rotationSpeed = 0.05 + voiceAmplitude * 0.1

    for (let i = 0; i < particleCount; i++) {
      const bx = basePositions[i * 3]
      const by = basePositions[i * 3 + 1]
      const bz = basePositions[i * 3 + 2]

      const angle = timeRef.current * rotationSpeed
      const cosA = Math.cos(angle)
      const sinA = Math.sin(angle)
      arr[i * 3] = (bx * cosA - bz * sinA) * pulseScale
      arr[i * 3 + 1] = by * pulseScale
      arr[i * 3 + 2] = (bx * sinA + bz * cosA) * pulseScale
    }
    posAttr.needsUpdate = true
  })

  return (
    <group position={[0, 0.5, 0]}>
      <points ref={meshRef} geometry={geometry} material={material} />
      <mesh>
        <sphereGeometry args={[2.2, 32, 32]} />
        <meshBasicMaterial color="#6a9c79" transparent opacity={0.06} side={THREE.BackSide} />
      </mesh>
    </group>
  )
}
