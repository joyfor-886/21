'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const DEBRIS_COUNT = 60

interface Props {
  isActive: boolean
}

export default function L3TextFlow({ isActive }: Props) {
  const groupRef = useRef<THREE.Group>(null)
  const debrisRef = useRef<THREE.Points>(null)
  const opacityRef = useRef(0)

  const { debrisPositions, debrisVelocities } = useMemo(() => {
    const pos = new Float32Array(DEBRIS_COUNT * 3)
    const vel = new Float32Array(DEBRIS_COUNT * 3)

    for (let i = 0; i < DEBRIS_COUNT; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 8
      pos[i * 3 + 1] = (Math.random() - 0.5) * 6
      pos[i * 3 + 2] = 1 + Math.random() * 2

      vel[i * 3] = (Math.random() - 0.5) * 0.02
      vel[i * 3 + 1] = Math.random() * 0.01 + 0.005
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.01
    }
    return { debrisPositions: pos, debrisVelocities: vel }
  }, [])

  const debrisGeometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(debrisPositions, 3))
    return geo
  }, [debrisPositions])

  const debrisMaterial = useMemo(() => {
    return new THREE.PointsMaterial({
      color: '#d4cbb8',
      size: 0.06,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      sizeAttenuation: true,
    })
  }, [])

  useFrame((_, delta) => {
    if (!debrisRef.current || !groupRef.current) return

    const targetOpacity = isActive ? 0.8 : 0.0
    opacityRef.current = THREE.MathUtils.lerp(opacityRef.current, targetOpacity, delta * 2)
    debrisMaterial.opacity = opacityRef.current

    const posAttr = debrisRef.current.geometry.attributes.position
    const arr = posAttr.array as Float32Array

    for (let i = 0; i < DEBRIS_COUNT; i++) {
      arr[i * 3] += debrisVelocities[i * 3] * (isActive ? 1 : 0.1)
      arr[i * 3 + 1] += debrisVelocities[i * 3 + 1] * (isActive ? 1 : 0.1)
      arr[i * 3 + 2] += debrisVelocities[i * 3 + 2] * (isActive ? 1 : 0.1)

      if (arr[i * 3 + 1] > 5) {
        arr[i * 3] = (Math.random() - 0.5) * 8
        arr[i * 3 + 1] = -3
        arr[i * 3 + 2] = 1 + Math.random() * 2
      }
    }
    posAttr.needsUpdate = true
  })

  return (
    <group ref={groupRef}>
      <points ref={debrisRef} geometry={debrisGeometry} material={debrisMaterial} />
    </group>
  )
}
