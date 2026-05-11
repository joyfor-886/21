'use client'

import { useRef, useEffect, useCallback } from 'react'
import { PHASE_COLORS } from '../../types/consciousness'
import type { ProjectOrb } from '../../types/consciousness'

export interface WaveConfig {
  w1Amp: number; w1Speed: number; w1Freq: number; w1DirX: number; w1DirZ: number;
  w2Amp: number; w2Speed: number; w2Freq: number; w2DirX: number; w2DirZ: number;
  w3Amp: number; w3Speed: number; w3Freq: number; w3DirX: number; w3DirZ: number;
  w4Amp: number; w4Speed: number; w4Freq: number; w4DirX: number; w4DirZ: number;
  w5Amp: number; w5Speed: number;
  cameraPitch: number; cameraY: number; cameraHeightBase: number;
  particleSizeBase: number;
  particleSizeJitter: number;
  particleOpacityBase: number;
  particleColorRGB: string;
  gridSpacingX: number;
  gridSpacingZ: number;
  gridJitter: number;
  oceanWidth: number;
  oceanDepth: number;
}

export const defaultWaveConfig: WaveConfig = {
  w1Amp: 20, w1Speed: 0.8, w1Freq: 0.004, w1DirX: 1, w1DirZ: 0.8,
  w2Amp: 12, w2Speed: 0.6, w2Freq: 0.006, w2DirX: 1, w2DirZ: -1.2,
  w3Amp: 8,  w3Speed: 1.2, w3Freq: 0.015, w3DirX: 1, w3DirZ: -0.7,
  w4Amp: 4,  w4Speed: 1.5, w4Freq: 0.030, w4DirX: 1, w4DirZ: 0.9,
  w5Amp: 6,  w5Speed: 0.3,

  cameraPitch: 45,
  cameraY: 150,
  cameraHeightBase: 500,

  particleSizeBase: 0.6,
  particleSizeJitter: 1.2,
  particleOpacityBase: 0.7,
  particleColorRGB: '255, 255, 255',
  gridSpacingX: 28,
  gridSpacingZ: 28,
  gridJitter: 0.3,
  oceanWidth: 5200,
  oceanDepth: 3600,
}

interface Props {
  voiceAmplitude?: number
  isDark?: boolean
  config?: WaveConfig
  orbs?: ProjectOrb[]
  onOrbClick?: (orbId: string) => void
}

export default function L4InkSea({ voiceAmplitude = 0, isDark = true, config, orbs = [], onOrbClick }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const configRef = useRef(config || defaultWaveConfig)
  const oceanParticlesRef = useRef<{ x: number; z: number; size: number; opMult: number }[]>([])
  const lastGridStrRef = useRef('')
  const voiceRef = useRef(voiceAmplitude)
  const orbsRef = useRef(orbs)
  const orbScreenPositionsRef = useRef<{ id: string; x: number; y: number; radius: number }[]>([])
  const onOrbClickRef = useRef(onOrbClick)
  const orbStatesRef = useRef<Map<string, { x: number; z: number; driftVx: number; driftVz: number }>>(new Map())
  const orbParticleOffsetsRef = useRef<Map<string, { theta: number; phi: number; rNorm: number; speed: number }[]>>(new Map())
  const gradientsRef = useRef<{
    key: string
    bg: CanvasGradient | null
    nebula1: CanvasGradient | null
    nebula2: CanvasGradient | null
    haze: CanvasGradient | null
    vignette: CanvasGradient | null
    bottom: CanvasGradient | null
  }>({ key: '', bg: null, nebula1: null, nebula2: null, haze: null, vignette: null, bottom: null })

  useEffect(() => { voiceRef.current = voiceAmplitude }, [voiceAmplitude])
  useEffect(() => { configRef.current = config || defaultWaveConfig }, [config])
  useEffect(() => { orbsRef.current = orbs }, [orbs])
  useEffect(() => { onOrbClickRef.current = onOrbClick }, [onOrbClick])

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const clickY = e.clientY - rect.top

    for (const pos of orbScreenPositionsRef.current) {
      const dx = clickX - pos.x
      const dy = clickY - pos.y
      if (dx * dx + dy * dy < pos.radius * pos.radius) {
        onOrbClickRef.current?.(pos.id)
        return
      }
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    let width = canvas.width = window.innerWidth
    let height = canvas.height = window.innerHeight
    let time = 0
    let animationFrameId: number

    const dust: { x: number; y: number; z: number; speed: number; radius: number }[] = []
    for (let i = 0; i < 300; i++) {
      dust.push({
        x: (Math.random() - 0.5) * 4000,
        y: (Math.random() - 0.5) * 1500,
        z: Math.random() * 3600 + 100,
        speed: Math.random() * 0.6 + 0.1,
        radius: Math.random() * 1.2 + 0.4,
      })
    }

    const stars: { x: number; y: number; z: number; radius: number; twinkleSpeed: number; twinklePhase: number }[] = []
    for (let i = 0; i < 200; i++) {
      stars.push({
        x: (Math.random() - 0.5) * 5000,
        y: -300 - Math.random() * 1200,
        z: Math.random() * 3500 + 200,
        radius: Math.random() * 1.5 + 0.3,
        twinkleSpeed: Math.random() * 3 + 1.5,
        twinklePhase: Math.random() * Math.PI * 2,
      })
    }

    const getWaveY = (px: number, pz: number, t: number, conf: WaveConfig, voiceBoost: number) => {
      const swell1 = Math.sin(px * conf.w1Freq * conf.w1DirX + t * conf.w1Speed + pz * conf.w1Freq * conf.w1DirZ) * (conf.w1Amp + voiceBoost)
      const swell2 = Math.cos(px * conf.w2Freq * conf.w2DirX - t * conf.w2Speed + pz * conf.w2Freq * conf.w2DirZ) * conf.w2Amp
      const ripple1 = Math.sin(px * conf.w3Freq * conf.w3DirX + t * conf.w3Speed + pz * conf.w3Freq * conf.w3DirZ) * (conf.w3Amp + voiceBoost * 0.5)
      const ripple2 = Math.cos(px * conf.w4Freq * conf.w4DirX - t * conf.w4Speed + pz * conf.w4Freq * conf.w4DirZ) * conf.w4Amp
      const breath = Math.sin(t * conf.w5Speed + px * 0.001) * conf.w5Amp
      return swell1 + swell2 + ripple1 + ripple2 + breath
    }

    const render = () => {
      time += 0.012
      const gradientKey = `${width}-${height}-${isDark}`
      const gradCache = gradientsRef.current
      if (gradientKey !== gradCache.key) {
        gradCache.key = gradientKey

        const bg = ctx.createLinearGradient(0, 0, 0, height)
        if (isDark) {
          bg.addColorStop(0, '#000000')
          bg.addColorStop(0.15, '#020204')
          bg.addColorStop(0.35, '#050507')
          bg.addColorStop(0.55, '#08080b')
          bg.addColorStop(0.75, '#0b0a0e')
          bg.addColorStop(1, '#0f0e12')
        } else {
          bg.addColorStop(0, '#c8c4bc')
          bg.addColorStop(0.3, '#d8d4cc')
          bg.addColorStop(0.6, '#e4e0d8')
          bg.addColorStop(1, '#f0ede5')
        }
        gradCache.bg = bg

        if (isDark) {
          const n1 = ctx.createRadialGradient(
            width * 0.3, height * 0.15, 0,
            width * 0.3, height * 0.15, width * 0.4
          )
          n1.addColorStop(0, 'rgba(20, 15, 40, 0.3)')
          n1.addColorStop(0.5, 'rgba(12, 8, 25, 0.15)')
          n1.addColorStop(1, 'rgba(0, 0, 0, 0)')
          gradCache.nebula1 = n1

          const n2 = ctx.createRadialGradient(
            width * 0.75, height * 0.25, 0,
            width * 0.75, height * 0.25, width * 0.35
          )
          n2.addColorStop(0, 'rgba(10, 20, 35, 0.25)')
          n2.addColorStop(0.6, 'rgba(5, 10, 20, 0.1)')
          n2.addColorStop(1, 'rgba(0, 0, 0, 0)')
          gradCache.nebula2 = n2
        } else {
          gradCache.nebula1 = null
          gradCache.nebula2 = null
        }

        const horizonY = height * 0.65
        const haze = ctx.createLinearGradient(0, horizonY - 80, 0, horizonY + 60)
        if (isDark) {
          haze.addColorStop(0, 'rgba(0, 0, 0, 0)')
          haze.addColorStop(0.4, 'rgba(15, 12, 20, 0.15)')
          haze.addColorStop(0.7, 'rgba(20, 18, 28, 0.25)')
          haze.addColorStop(1, 'rgba(0, 0, 0, 0)')
        } else {
          haze.addColorStop(0, 'rgba(240, 237, 229, 0)')
          haze.addColorStop(0.5, 'rgba(230, 225, 215, 0.2)')
          haze.addColorStop(1, 'rgba(240, 237, 229, 0)')
        }
        gradCache.haze = haze

        const vigCx = width / 2
        const vigCy = height * 0.45
        const vigR = Math.max(width, height) * 0.8
        const vig = ctx.createRadialGradient(vigCx, vigCy, vigR * 0.3, vigCx, vigCy, vigR)
        if (isDark) {
          vig.addColorStop(0, 'rgba(0, 0, 0, 0)')
          vig.addColorStop(0.6, 'rgba(0, 0, 0, 0)')
          vig.addColorStop(1, 'rgba(0, 0, 0, 0.5)')
        } else {
          vig.addColorStop(0, 'rgba(0, 0, 0, 0)')
          vig.addColorStop(0.6, 'rgba(0, 0, 0, 0)')
          vig.addColorStop(1, 'rgba(0, 0, 0, 0.12)')
        }
        gradCache.vignette = vig

        const bottomGradHeight = height * 0.5
        const bottom = ctx.createLinearGradient(0, height - bottomGradHeight, 0, height)
        if (isDark) {
          bottom.addColorStop(0, 'rgba(0, 0, 0, 0)')
          bottom.addColorStop(0.5, 'rgba(0, 0, 0, 0.6)')
          bottom.addColorStop(1, 'rgba(0, 0, 0, 1)')
        } else {
          bottom.addColorStop(0, 'rgba(240, 237, 229, 0)')
          bottom.addColorStop(0.5, 'rgba(240, 237, 229, 0.7)')
          bottom.addColorStop(1, 'rgba(240, 237, 229, 1)')
        }
        gradCache.bottom = bottom
      }

      ctx.fillStyle = gradCache.bg!
      ctx.fillRect(0, 0, width, height)

      if (gradCache.nebula1) {
        ctx.fillStyle = gradCache.nebula1
        ctx.fillRect(0, 0, width, height)
      }
      if (gradCache.nebula2) {
        ctx.fillStyle = gradCache.nebula2
        ctx.fillRect(0, 0, width, height)
      }

      const horizonY = height * 0.65
      ctx.fillStyle = gradCache.haze!
      ctx.fillRect(0, horizonY - 80, width, 140)

      ctx.fillStyle = gradCache.vignette!
      ctx.fillRect(0, 0, width, height)

      const conf = configRef.current
      const voice = voiceRef.current

      const gridStr = `${conf.gridSpacingX},${conf.gridSpacingZ},${conf.gridJitter},${conf.particleSizeBase},${conf.particleSizeJitter},${conf.particleOpacityBase},${conf.oceanWidth},${conf.oceanDepth}`
      if (gridStr !== lastGridStrRef.current) {
        lastGridStrRef.current = gridStr
        const xCount = Math.floor(conf.oceanWidth / conf.gridSpacingX)
        const zCount = Math.floor(conf.oceanDepth / conf.gridSpacingZ)
        const newParticles: { x: number; z: number; size: number; opMult: number }[] = []
        for (let z = 0; z < zCount; z++) {
          for (let x = 0; x < xCount; x++) {
            const jitterX = (Math.random() - 0.5) * conf.gridSpacingX * conf.gridJitter
            const jitterZ = (Math.random() - 0.5) * conf.gridSpacingZ * conf.gridJitter
            newParticles.push({
              x: (x - xCount / 2) * conf.gridSpacingX + jitterX,
              z: z * conf.gridSpacingZ - 300 + jitterZ,
              size: Math.random() * conf.particleSizeJitter + conf.particleSizeBase,
              opMult: Math.random() * (1 - conf.particleOpacityBase) + conf.particleOpacityBase,
            })
          }
        }
        oceanParticlesRef.current = newParticles
      }

      const oceanParticles = oceanParticlesRef.current

      const cx = width / 2
      const cy = height / 2 + conf.cameraHeightBase
      const fov = 500

      const pitch = conf.cameraPitch * (Math.PI / 180)
      const cosPitch = Math.cos(pitch)
      const sinPitch = Math.sin(pitch)
      const cameraY = conf.cameraY

      const colorRGB = isDark ? conf.particleColorRGB : '60, 55, 48'
      ctx.fillStyle = `rgba(${colorRGB}, 1)`

      const voiceAmpBoost = voice * 8

      for (let i = oceanParticles.length - 1; i >= 0; i--) {
        const p = oceanParticles[i]

        const swell1 = Math.sin(p.x * conf.w1Freq * conf.w1DirX + time * conf.w1Speed + p.z * conf.w1Freq * conf.w1DirZ) * (conf.w1Amp + voiceAmpBoost)
        const swell2 = Math.cos(p.x * conf.w2Freq * conf.w2DirX - time * conf.w2Speed + p.z * conf.w2Freq * conf.w2DirZ) * conf.w2Amp
        const ripple1 = Math.sin(p.x * conf.w3Freq * conf.w3DirX + time * conf.w3Speed + p.z * conf.w3Freq * conf.w3DirZ) * (conf.w3Amp + voiceAmpBoost * 0.5)
        const ripple2 = Math.cos(p.x * conf.w4Freq * conf.w4DirX - time * conf.w4Speed + p.z * conf.w4Freq * conf.w4DirZ) * conf.w4Amp
        const breath = Math.sin(time * conf.w5Speed + p.x * 0.001) * conf.w5Amp

        const waveY = swell1 + swell2 + ripple1 + ripple2 + breath

        const relY = waveY - cameraY
        const relZ = p.z

        const rotY = relY * cosPitch - relZ * sinPitch
        const rotZ = relY * sinPitch + relZ * cosPitch

        if (rotZ < -fov + 10) continue

        const scale = fov / (fov + rotZ)
        const x2d = p.x * scale + cx
        const y2d = rotY * scale + cy

        let opacity = Math.min(1, Math.max(0, 1 - p.z / conf.oceanDepth))

        if (rotZ < 150) {
          opacity *= Math.max(0, (rotZ + fov - 10) / (fov + 140))
        }

        opacity *= p.opMult

        if (x2d > -100 && x2d < width + 100 && y2d > -100 && y2d < height + 300 && opacity > 0.02) {
          ctx.globalAlpha = opacity
          const s = p.size * scale * (waveY > 0 ? 1.2 : 0.8)
          ctx.fillRect(x2d, y2d, s, s)
        }
      }

      const currentOrbs = orbsRef.current
      const orbScreenPositions: { id: string; x: number; y: number; radius: number }[] = []
      const orbStates = orbStatesRef.current

      for (const orb of currentOrbs) {
        if (!orbStates.has(orb.id)) {
          orbStates.set(orb.id, { x: orb.x, z: orb.z, driftVx: orb.driftVx, driftVz: orb.driftVz })
        }
        const state = orbStates.get(orb.id)!

        state.driftVx *= 0.995
        state.driftVz *= 0.995

        state.x += state.driftVx
        state.z += state.driftVz

        const halfW = conf.oceanWidth * 0.35
        const minZ = 150
        const maxZ = conf.oceanDepth * 0.55

        if (state.x > halfW) {
          state.x = halfW
          state.driftVx = -Math.abs(state.driftVx) * 0.6
        }
        if (state.x < -halfW) {
          state.x = -halfW
          state.driftVx = Math.abs(state.driftVx) * 0.6
        }
        if (state.z > maxZ) {
          state.z = maxZ
          state.driftVz = -Math.abs(state.driftVz) * 0.6
        }
        if (state.z < minZ) {
          state.z = minZ
          state.driftVz = Math.abs(state.driftVz) * 0.6
        }

        const conversationZoneX = conf.oceanWidth * 0.18
        const conversationZoneZMin = 200
        const conversationZoneZMax = 450

        if (state.x > -conversationZoneX && state.x < conversationZoneX &&
            state.z > conversationZoneZMin && state.z < conversationZoneZMax) {
          const pushDir = state.x >= 0 ? 1 : -1
          state.driftVx = pushDir * 0.3
          state.driftVz = -0.15
        }

        const orbWaveY = getWaveY(state.x, state.z, time, conf, voiceAmpBoost)

        const relY = orbWaveY - cameraY
        const relZ = state.z

        const rotY = relY * cosPitch - relZ * sinPitch
        const rotZ = relY * sinPitch + relZ * cosPitch

        if (rotZ < -fov + 10) continue

        const scale = fov / (fov + rotZ)
        const x2d = state.x * scale + cx
        const y2d = rotY * scale + cy

        const screenRadius = orb.radius * scale * 2.5

        const phaseColor = PHASE_COLORS[orb.phase] || PHASE_COLORS.qishu
        const { r, g, b } = phaseColor

        const glowGrad = ctx.createRadialGradient(x2d, y2d, 0, x2d, y2d, screenRadius * 2.5)
        glowGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${orb.isCurrent ? 0.15 : 0.06})`)
        glowGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${orb.isCurrent ? 0.04 : 0.015})`)
        glowGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
        ctx.globalAlpha = 1
        ctx.fillStyle = glowGrad
        ctx.fillRect(x2d - screenRadius * 2.5, y2d - screenRadius * 2.5, screenRadius * 5, screenRadius * 5)

        const orbParticles = orbParticleOffsetsRef.current
        if (!orbParticles.has(orb.id)) {
          const count = orb.isCurrent ? 400 : 250
          const goldenAngle = Math.PI * (3 - Math.sqrt(5))
          const offsets: { theta: number; phi: number; rNorm: number; speed: number }[] = []
          for (let i = 0; i < count; i++) {
            const yNorm = 1 - (i / (count - 1)) * 2
            const radiusAtY = Math.sqrt(Math.max(0, 1 - yNorm * yNorm))
            const theta = goldenAngle * i
            offsets.push({
              theta,
              phi: Math.asin(yNorm),
              rNorm: radiusAtY,
              speed: 0.04 + Math.random() * 0.02,
            })
          }
          orbParticles.set(orb.id, offsets)
        }

        const particles = orbParticles.get(orb.id)!
        const rotAngle = time * 0.04
        const cosRot = Math.cos(rotAngle)
        const sinRot = Math.sin(rotAngle)

        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 1)`

        for (let i = 0; i < particles.length; i++) {
          const p = particles[i]
          const localX = Math.cos(p.theta + time * p.speed) * p.rNorm
          const localY = Math.sin(p.phi)
          const localZ = Math.sin(p.theta + time * p.speed) * p.rNorm

          const rx = localX * cosRot - localZ * sinRot
          const ry = localY
          const rz = localX * sinRot + localZ * cosRot

          const depthFactor = (rz + 1) * 0.5
          const pAlpha = (0.25 + depthFactor * 0.55) * (orb.isCurrent ? 1 : 0.5)
          const pSize = Math.max(0.5, (1.0 + depthFactor * 1.5) * screenRadius * 0.014)
          const px = x2d + rx * screenRadius * 0.9
          const py = y2d + ry * screenRadius * 0.9

          ctx.globalAlpha = pAlpha
          ctx.fillRect(px - pSize * 0.5, py - pSize * 0.5, pSize, pSize)
        }

        if (screenRadius > 15) {
          ctx.globalAlpha = orb.isCurrent ? 0.95 : 0.6
          ctx.fillStyle = isDark ? '#ffffff' : '#1a1a1a'
          ctx.font = `${Math.max(9, screenRadius * 0.35)}px "Noto Serif SC", "Songti SC", serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(orb.phaseLabel, x2d, y2d)
        }

        orbScreenPositions.push({ id: orb.id, x: x2d, y: y2d, radius: screenRadius })
      }

      orbScreenPositionsRef.current = orbScreenPositions

      const dustColorRGB = isDark ? '255, 255, 255' : '80, 75, 65'
      ctx.fillStyle = `rgba(${dustColorRGB}, 0.5)`
      for (let i = 0; i < dust.length; i++) {
        const d = dust[i]
        d.y -= d.speed
        d.x += Math.sin(d.y * 0.005) * 0.5

        if (d.y < -800) d.y = 800

        const relZ = d.z
        const relY = d.y - cameraY

        const rotY = relY * cosPitch - relZ * sinPitch
        const rotZ = relY * sinPitch + relZ * cosPitch

        if (rotZ < -fov + 10) continue

        const scale = fov / (fov + rotZ)
        const x2d = d.x * scale + cx
        const y2d = rotY * scale + cy - 200

        if (x2d > 0 && x2d < width && y2d > 0 && y2d < height) {
          ctx.globalAlpha = 1
          ctx.beginPath()
          ctx.arc(x2d, y2d, d.radius * scale, 0, Math.PI * 2)
          ctx.fill()
        }
      }

      const starColorRGB = isDark ? '255, 255, 255' : '120, 115, 105'
      for (let i = 0; i < stars.length; i++) {
        const st = stars[i]
        const relZ = st.z
        const relY = st.y - cameraY

        const rotY = relY * cosPitch - relZ * sinPitch
        const rotZ = relY * sinPitch + relZ * cosPitch

        if (rotZ < -fov + 10) continue

        const scale = fov / (fov + rotZ)
        const x2d = st.x * scale + cx
        const y2d = rotY * scale + cy

        if (x2d > -50 && x2d < width + 50 && y2d > -200 && y2d < height * 0.7) {
          const twinkle = Math.sin(time * st.twinkleSpeed + st.twinklePhase)
          const alpha = twinkle * 0.5 + 0.5
          ctx.fillStyle = `rgba(${starColorRGB}, ${alpha})`
          ctx.globalAlpha = 1
          ctx.beginPath()
          ctx.arc(x2d, y2d, st.radius * scale * (twinkle * 0.3 + 0.8), 0, Math.PI * 2)
          ctx.fill()
        }
      }

      const bottomGradHeight = height * 0.5
      ctx.fillStyle = gradCache.bottom!
      ctx.fillRect(0, height - bottomGradHeight, width, bottomGradHeight)

      animationFrameId = requestAnimationFrame(render)
    }

    render()

    const handleResize = () => {
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', handleResize)
    }
  }, [isDark])

  return (
    <canvas
      ref={canvasRef}
      onClick={handleCanvasClick}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        cursor: 'default',
      }}
    />
  )
}
