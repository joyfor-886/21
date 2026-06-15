'use client'

import { useRef, useMemo, useState, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { Text } from '@react-three/drei'
import * as THREE from 'three'

const PHASE_LABELS: Record<string, string> = {
  qishu: '启枢',
  tanyin: '探隐',
  caiheng: '裁衡',
  zhenwei: '甄微',
  ceshu: '策书',
  ningmo: '凝墨',
}

interface Props {
  currentPhase: string
}

export default function L1Calligraphy3D({ currentPhase }: Props) {
  const groupRef = useRef<THREE.Group>(null)
  const [displayPhase, setDisplayPhase] = useState(currentPhase)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [rotationY, setRotationY] = useState(0)
  const [opacity, setOpacity] = useState(1)

  useEffect(() => {
    if (currentPhase === displayPhase) return
    setIsTransitioning(true)
    const outTimer = setTimeout(() => {
      setDisplayPhase(currentPhase)
      setRotationY(-Math.PI / 2)
      setOpacity(0)
    }, 500)
    const inTimer = setTimeout(() => {
      setIsTransitioning(false)
    }, 1000)
    return () => { clearTimeout(outTimer); clearTimeout(inTimer) }
  }, [currentPhase, displayPhase])

  useFrame((_, delta) => {
    if (!groupRef.current) return
    if (isTransitioning) {
      if (rotationY < Math.PI / 2 && displayPhase === currentPhase) {
        // already swapped, animate in
      }
    }
    const targetY = isTransitioning && displayPhase !== currentPhase ? Math.PI / 2 : 0
    const currentY = groupRef.current.rotation.y
    groupRef.current.rotation.y = THREE.MathUtils.lerp(currentY, targetY, delta * 4)
  })

  const label = PHASE_LABELS[displayPhase] || '启枢'

  return (
    <group ref={groupRef} position={[0, 1.2, -4]}>
      <Text
        fontSize={2.8}
        font="https://fonts.gstatic.com/s/notoserifsc/v12/H4c8BXePl9DZ0Xe7gG9cyOj7oqP9qGdN.ttf"
        color="#8a8070"
        anchorX="center"
        anchorY="middle"
        maxWidth={10}
        fillOpacity={0.15}
      >
        {label}
      </Text>
    </group>
  )
}
