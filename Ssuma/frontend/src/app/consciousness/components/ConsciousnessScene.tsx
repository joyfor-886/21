'use client'

import { Canvas } from '@react-three/fiber'
import React, { useRef, useMemo, useEffect } from 'react'
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
type VoiceVisualMode = 'ink-ripple' | 'liquid-wave' | 'silk-flow' | 'heartbeat'

// Global voice visual mode — switch with keyboard shortcut V
let globalVoiceVisualMode: VoiceVisualMode = 'ink-ripple'
export function getVoiceVisualMode() { return globalVoiceVisualMode }
export function setVoiceVisualMode(m: VoiceVisualMode) { globalVoiceVisualMode = m }
export function cycleVoiceVisualMode(): VoiceVisualMode {
  const modes: VoiceVisualMode[] = ['ink-ripple', 'liquid-wave', 'silk-flow', 'heartbeat']
  const idx = modes.indexOf(globalVoiceVisualMode)
  globalVoiceVisualMode = modes[(idx + 1) % modes.length]
  return globalVoiceVisualMode
}

interface InkSphereProps {
  isThinking?: boolean
  isDark?: boolean
  voiceAmplitude?: number
  voiceLowFreq?: number
  voiceMidFreq?: number
  voiceHighFreq?: number
}

function InkSphere({ isThinking = false, isDark = true, voiceAmplitude = 0, voiceLowFreq = 0, voiceMidFreq = 0, voiceHighFreq = 0 }: InkSphereProps) {
  const groupRef = useRef<THREE.Group>(null)
  const pointsRef = useRef<THREE.Points>(null)
  const modeRef = useRef<ThinkingMode>('vortex')
  const thinkStartRef = useRef(0)
  const prevThinkingRef = useRef(false)
  const timeRef = useRef(0)
  const voiceAmpRef = useRef(0)
  const voiceLowRef = useRef(0)
  const voiceMidRef = useRef(0)
  const voiceHighRef = useRef(0)
  // Smoothed values for fluid animation
  const smoothAmpRef = useRef(0)
  const smoothLowRef = useRef(0)
  const smoothMidRef = useRef(0)
  const smoothHighRef = useRef(0)

  useEffect(() => { voiceAmpRef.current = voiceAmplitude }, [voiceAmplitude])
  useEffect(() => { voiceLowRef.current = voiceLowFreq }, [voiceLowFreq])
  useEffect(() => { voiceMidRef.current = voiceMidFreq }, [voiceMidFreq])
  useEffect(() => { voiceHighRef.current = voiceHighFreq }, [voiceHighFreq])

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
      // Smooth interpolation for fluid motion
      const lerp = 1 - Math.pow(0.05, delta)
      smoothAmpRef.current += (voiceAmpRef.current - smoothAmpRef.current) * lerp
      smoothLowRef.current += (voiceLowRef.current - smoothLowRef.current) * lerp
      smoothMidRef.current += (voiceMidRef.current - smoothMidRef.current) * lerp
      smoothHighRef.current += (voiceHighRef.current - smoothHighRef.current) * lerp

      const amp = smoothAmpRef.current
      const low = smoothLowRef.current
      const mid = smoothMidRef.current
      const high = smoothHighRef.current
      const voiceMode = globalVoiceVisualMode

      // Base rotation — faster with voice
      const rotSpeed = 0.04 + amp * 0.08

      for (let i = 0; i < count; i++) {
        const angle = baseAngles[i] + t * rotSpeed
        const baseR = baseRadii[i]
        const baseY = basePositions[i * 3 + 1]
        const theta = Math.acos(Math.max(-1, Math.min(1, baseY / 2)))
        const phi = angle

        let px: number, py: number, pz: number

        if (voiceMode === 'ink-ripple') {
          // 墨滴涟漪: 粒子从球体表面向外流动，像墨水在水中扩散
          // 低频→大股墨流，中频→丝状蔓延，高频→墨点飞溅
          const flowOut = low * 0.5 + mid * 0.25 + high * 0.15
          const inkWave = Math.sin(t * 2.5 - theta * 3 + i * 0.01) * flowOut * 0.6
          const inkStrand = Math.sin(phi * 3 + t * 1.8) * mid * 0.25
          const inkSplash = Math.sin(i * 7.3 + t * 6) * high * 0.15
          const r = baseR * (1 + inkWave + inkStrand + inkSplash)
          const y = baseY * (1 + inkWave * 0.4)
          px = Math.cos(angle) * r
          py = y
          pz = Math.sin(angle) * r
        } else if (voiceMode === 'liquid-wave') {
          // 液态波动: 球体表面像水面一样产生同心波纹向外传播
          // 低频→大波浪，中频→细密涟漪，高频→表面碎波
          const bigWave = Math.sin(theta * 2 - t * 3) * low * 0.5
          const ripple = Math.sin(theta * 6 + phi * 2 - t * 5) * mid * 0.25
          const surfaceWave = Math.sin(theta * 12 + phi * 4 - t * 8) * high * 0.12
          const deform = 1 + bigWave + ripple + surfaceWave
          const r = baseR * deform
          const y = baseY * deform
          px = Math.cos(angle) * r
          py = y
          pz = Math.sin(angle) * r
        } else if (voiceMode === 'silk-flow') {
          // 丝绒飘动: 球体像被风吹动的丝带，粒子沿气流方向飘动
          // 低频→整体缓慢飘摇，中频→局部翻卷，高频→边缘丝线飘散
          const windX = Math.sin(t * 0.8 + i * 0.003) * low * 0.6
          const windY = Math.cos(t * 0.6 + i * 0.005) * low * 0.3
          const curlX = Math.sin(phi * 2 + t * 2.5) * mid * 0.35
          const curlY = Math.cos(theta * 3 + t * 2) * mid * 0.2
          const edgeFloat = (1 - Math.abs(Math.cos(theta))) * Math.sin(i * 3.7 + t * 4) * high * 0.3
          px = Math.cos(angle) * baseR + windX + curlX
          py = baseY + windY + curlY
          pz = Math.sin(angle) * baseR + edgeFloat
        } else {
          // 心跳脉冲: 球体像心跳一样有节奏地收缩扩张
          // 低频→大脉冲，中频→快速心跳，高频→表面颤动
          const pulse = Math.pow(Math.sin(t * 3), 8) * low * 0.6
          const heartbeat = Math.abs(Math.sin(t * 5 + 0.5)) * mid * 0.3
          const tremor = Math.sin(i * 5.1 + t * 10) * high * 0.1
          const deform = 1 + pulse + heartbeat + tremor
          const r = baseR * deform
          const y = baseY * deform
          px = Math.cos(angle) * r
          py = y
          pz = Math.sin(angle) * r
        }

        arr[i * 3] = px
        arr[i * 3 + 1] = py
        arr[i * 3 + 2] = pz
      }
      if (groupRef.current) groupRef.current.rotation.y += delta * rotSpeed
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
  voiceLowFreq?: number
  voiceMidFreq?: number
  voiceHighFreq?: number
  gradeColor?: string
  theme: 'xuanmo' | 'xuanzhi'
  isThinking: boolean
  orbs?: ProjectOrb[]
  onOrbClick?: (orbId: string) => void
}

export default function ConsciousnessScene({
  theme,
  voiceAmplitude,
  voiceLowFreq = 0,
  voiceMidFreq = 0,
  voiceHighFreq = 0,
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
          style={{ position: 'absolute', inset: 0, zIndex: 0, background: 'transparent', pointerEvents: 'none' }}
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[3, 5, 5]} intensity={0.6} />
          <pointLight position={[0, 2, 6]} intensity={0.35} color="#c8b89a" />

          <InkSphere isThinking={isThinking} isDark={isDark} voiceAmplitude={voiceAmplitude} voiceLowFreq={voiceLowFreq} voiceMidFreq={voiceMidFreq} voiceHighFreq={voiceHighFreq} />
        </Canvas>
      </SceneErrorBoundary>
    </>
  )
}
