'use client'

import { Canvas } from '@react-three/fiber'
import React, { useRef, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import L4InkSea from './layers/L4InkSea'
import type { ProjectOrb } from '../types/consciousness'

class SceneErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean}> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{position:'absolute',inset:0,background:'linear-gradient(180deg,#08090a 0%,#0f0e12 100%)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:0}}>
          <p style={{color:'#5a5549',fontSize:'13px',fontFamily:'"Noto Serif SC",serif'}}>意识空间加载中…</p>
        </div>
      )
    }
    return this.props.children
  }
}

type ThinkingMode = 'vortex' | 'breathing' | 'diffusion' | 'gravity'

interface InkSphereProps {
  isThinking?: boolean
  isDark?: boolean
}

function InkSphere({ isThinking = false, isDark = true }: InkSphereProps) {
  const groupRef = useRef<THREE.Group>(null)
  const pointsRef = useRef<THREE.Points>(null)
  const modeRef = useRef<ThinkingMode>('vortex')
  const thinkStartRef = useRef(0)
  const prevThinkingRef = useRef(false)
  const timeRef = useRef(0)

  const count = 600

  const particleColor = isDark ? '#e8e4dc' : '#3a3530'
  const materialColor = isDark ? '#6a9c79' : '#4a7c59'

  const { basePositions, baseAngles, baseRadii } = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const angles = new Float32Array(count)
    const radii = new Float32Array(count)

    const goldenAngle = Math.PI * (3 - Math.sqrt(5))

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2
      const r = Math.sqrt(1 - y * y) * 2
      const theta = goldenAngle * i

      positions[i * 3] = Math.cos(theta) * r
      positions[i * 3 + 1] = y * 2
      positions[i * 3 + 2] = Math.sin(theta) * r

      angles[i] = theta
      radii[i] = r
    }

    return { basePositions: positions, baseAngles: angles, baseRadii: radii }
  }, [])

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(basePositions.slice(), 3))
    return geo
  }, [basePositions])

  useFrame((_, delta) => {
    if (!pointsRef.current) return

    timeRef.current += delta
    const t = timeRef.current
    const posAttr = pointsRef.current.geometry.getAttribute('position') as THREE.BufferAttribute
    const arr = posAttr.array as Float32Array

    if (isThinking && !prevThinkingRef.current) {
      const modes: ThinkingMode[] = ['vortex', 'breathing', 'diffusion', 'gravity']
      modeRef.current = modes[Math.floor(Math.random() * modes.length)]
      thinkStartRef.current = t
    }
    prevThinkingRef.current = isThinking

    if (!isThinking) {
      for (let i = 0; i < count; i++) {
        const angle = baseAngles[i] + t * 0.04
        const r = baseRadii[i]
        const y = basePositions[i * 3 + 1]
        arr[i * 3] = Math.cos(angle) * r
        arr[i * 3 + 1] = y
        arr[i * 3 + 2] = Math.sin(angle) * r
      }
      if (groupRef.current) groupRef.current.rotation.y += delta * 0.04
      posAttr.needsUpdate = true
      return
    }

    const thinkT = t - thinkStartRef.current
    const mode = modeRef.current

    if (mode === 'vortex') {
      const spiralSpeed = 0.8 + Math.sin(thinkT * 0.6) * 0.4
      const collapsePhase = (Math.sin(thinkT * 1.4) + 1) * 0.5
      for (let i = 0; i < count; i++) {
        const baseAngle = baseAngles[i]
        const direction = i % 2 === 0 ? 1 : -1
        const angle = baseAngle + t * spiralSpeed * direction
        const shrinkFactor = 0.7 + (1 - collapsePhase) * 0.3
        const wobble = Math.sin(t * 3 + i * 0.7) * 0.03
        const r = baseRadii[i] * shrinkFactor * (1 + wobble)
        const y = basePositions[i * 3 + 1] * shrinkFactor
        arr[i * 3] = Math.cos(angle) * r
        arr[i * 3 + 1] = y
        arr[i * 3 + 2] = Math.sin(angle) * r
      }
      if (groupRef.current) groupRef.current.rotation.y += delta * spiralSpeed * 0.4
    } else if (mode === 'breathing') {
      const breathPhase = Math.sin(thinkT * 1.6)
      const scale = 1 + breathPhase * 0.16
      for (let i = 0; i < count; i++) {
        const angle = baseAngles[i] + t * 0.06
        const pulseOffset = Math.sin(i * 0.05 + thinkT * 2) * 0.04
        const r = baseRadii[i] * scale * (1 + pulseOffset)
        const y = basePositions[i * 3 + 1] * scale
        arr[i * 3] = Math.cos(angle) * r
        arr[i * 3 + 1] = y
        arr[i * 3 + 2] = Math.sin(angle) * r
      }
      if (groupRef.current) groupRef.current.rotation.y += delta * 0.04
    } else if (mode === 'diffusion') {
      const diffusePhase = (Math.sin(thinkT * 0.7) + 1) * 0.5
      for (let i = 0; i < count; i++) {
        const angle = baseAngles[i] + t * 0.04 + Math.sin(i * 1.3) * 0.12
        const expand = 1 + diffusePhase * 0.35
        const jitterX = Math.sin(t * 2.5 + i * 0.9) * 0.05 * diffusePhase
        const jitterY = Math.cos(t * 2 + i * 1.1) * 0.05 * diffusePhase
        const jitterZ = Math.sin(t * 1.8 + i * 0.6) * 0.05 * diffusePhase
        const r = baseRadii[i] * expand
        const y = basePositions[i * 3 + 1] * expand
        arr[i * 3] = Math.cos(angle) * r + jitterX
        arr[i * 3 + 1] = y + jitterY
        arr[i * 3 + 2] = Math.sin(angle) * r + jitterZ
      }
      if (groupRef.current) groupRef.current.rotation.y += delta * 0.02
    } else if (mode === 'gravity') {
      const pullStrength = (Math.sin(thinkT * 1.3) + 1) * 0.5
      for (let i = 0; i < count; i++) {
        const orbitSpeed = 0.15 + (1 - i / count) * 0.35
        const angle = baseAngles[i] + t * orbitSpeed
        const orbitExpand = 1 + Math.sin(t * 0.4 + i * 0.2) * 0.08
        const shrink = 1 - pullStrength * 0.18
        const r = baseRadii[i] * orbitExpand * shrink
        const y = basePositions[i * 3 + 1] * shrink
        arr[i * 3] = Math.cos(angle) * r
        arr[i * 3 + 1] = y
        arr[i * 3 + 2] = Math.sin(angle) * r
      }
      if (groupRef.current) groupRef.current.rotation.y += delta * 0.07
    }

    posAttr.needsUpdate = true
  })

  return (
    <group ref={groupRef} position={[0, 1.3, -3]}>
      <points ref={pointsRef} geometry={geometry}>
        <pointsMaterial
          color={particleColor}
          size={0.035}
          transparent
          opacity={0.95}
          sizeAttenuation
          depthWrite={false}
        />
      </points>
    </group>
  )
}

interface Props {
  currentPhase: string
  voiceAmplitude: number
  gradeColor?: string
  theme: 'xuanmo' | 'xuanzhi'
  isThinking: boolean
  orbs?: ProjectOrb[]
  onOrbClick?: (orbId: string) => void
}

export default function ConsciousnessScene({
  theme,
  voiceAmplitude,
  orbs = [],
  onOrbClick,
  isThinking = false,
}: Props) {
  const isDark = theme === 'xuanmo'

  return (
    <>
      <L4InkSea
        voiceAmplitude={voiceAmplitude}
        isDark={isDark}
        orbs={orbs}
        onOrbClick={onOrbClick}
      />
      <SceneErrorBoundary>
        <Canvas
          className="scene-canvas"
          camera={{ position: [0, 0, 8], fov: 50 }}
          gl={{ antialias: true, alpha: true }}
          style={{ position: 'absolute', inset: 0, zIndex: 1, background: 'transparent', pointerEvents: 'none' }}
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[3, 5, 5]} intensity={0.6} />
          <pointLight position={[0, 2, 6]} intensity={0.35} color="#c8b89a" />

          <InkSphere isThinking={isThinking} isDark={isDark} />
        </Canvas>
      </SceneErrorBoundary>
    </>
  )
}
