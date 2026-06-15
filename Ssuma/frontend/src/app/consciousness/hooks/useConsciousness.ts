'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ProjectOrb, InteractiveOption } from '../types/consciousness'
import type { HITLInterrupt } from '../../../lib/types'
import { useChatStream } from './useChatStream'
import { useVoiceMode } from './useVoiceMode'
import { useTTS } from './useTTS'
import { cycleVoiceVisualMode } from '../components/ConsciousnessScene'
import { useTanyin } from './useTanyin'
import { useFlowContext } from '../context/FlowContext'
import { PHASE_LABELS } from '../../../lib/constants'

interface UseConsciousnessReturn {
  // Chat
  messages: ReturnType<typeof useChatStream>['messages']
  loading: boolean
  loadingProgress: number
  handleSend: (content: string) => Promise<void>
  handleOptionClick: (option: InteractiveOption) => void
  // Voice
  voiceState: ReturnType<typeof useVoiceMode>['voiceState']
  isVoiceMode: boolean
  voiceVisualLabel: string
  // Tanyin
  tanyin: ReturnType<typeof useTanyin>['tanyin']
  answers: ReturnType<typeof useTanyin>['answers']
  textAnswers: ReturnType<typeof useTanyin>['textAnswers']
  closeTanyin: () => void
  toggleOption: ReturnType<typeof useTanyin>['toggleOption']
  setRadioOption: ReturnType<typeof useTanyin>['setRadioOption']
  setTextAnswer: ReturnType<typeof useTanyin>['setTextAnswer']
  handleTanyinSubmit: () => void
  // State
  thinkingStartTime: number
  // HITL
  hitlInterrupt: HITLInterrupt | null
  clearHITL: () => void
}

export function useConsciousness(): UseConsciousnessReturn {
  const { state, dispatch, refreshStatus, handlePhaseClick, handleApplyConfig, handleOrbClick } = useFlowContext()
  const { projectId, currentPhase, artifacts } = state

  const { messages, loading, loadingProgress, sendMessage, hitlInterrupt, clearHITL } = useChatStream()
  const { speak } = useTTS()

  const handleSendRef = useRef<(content: string) => Promise<void>>(undefined as unknown as (content: string) => Promise<void>)

  const handleVoiceTranscript = useCallback((text: string) => {
    lastVoiceUsedRef.current = true
    handleSendRef.current?.(text)
  }, [])

  const { voiceState, startListening, stopListening } = useVoiceMode(handleVoiceTranscript)
  const {
    tanyin, answers, textAnswers, closeTanyin,
    toggleOption, setRadioOption, setTextAnswer, submitAnswers,
  } = useTanyin()

  const sessionOrbIdRef = useRef<string | null>(null)
  const thinkingStartRef = useRef<number>(0)
  const projectIdRef = useRef(projectId)
  const currentPhaseRef = useRef(currentPhase)
  const refreshStatusRef = useRef(refreshStatus)

  useEffect(() => {
    projectIdRef.current = projectId
    currentPhaseRef.current = currentPhase
    refreshStatusRef.current = refreshStatus
  }, [projectId, currentPhase, refreshStatus])

  useEffect(() => {
    if (loading) {
      if (thinkingStartRef.current === 0) thinkingStartRef.current = Date.now()
    } else {
      thinkingStartRef.current = 0
    }
  }, [loading])

  const orbMessagesRef = useRef(messages)
  const orbArtifactsRef = useRef(artifacts)
  useEffect(() => { orbMessagesRef.current = messages }, [messages])
  useEffect(() => { orbArtifactsRef.current = artifacts }, [artifacts])

  useEffect(() => {
    if (!projectId) return
    dispatch({
      type: 'UPDATE_ORB',
      payload: {
        projectId,
        updates: {
          phase: currentPhase,
          phaseLabel: PHASE_LABELS[currentPhase]?.label || currentPhase,
          isCurrent: true,
          messages: [...orbMessagesRef.current],
          artifacts: orbArtifactsRef.current.map((a) => a.phase || a.summary),
        },
      },
    })
  }, [projectId, currentPhase])

  const handleSend = useCallback(async (content: string) => {
    if (!sessionOrbIdRef.current) {
      const tempId = `orb-session-${Date.now()}`
      sessionOrbIdRef.current = tempId
      const phaseLabel = PHASE_LABELS[currentPhaseRef.current]?.label || currentPhaseRef.current
      const newOrb: ProjectOrb = {
        id: tempId,
        projectId: projectIdRef.current || 'temp',
        phase: currentPhaseRef.current,
        phaseLabel,
        x: (Math.random() - 0.5) * 300 + (Math.random() > 0.5 ? 250 : -250),
        z: Math.random() * 400 + 200,
        driftVx: (Math.random() - 0.5) * 0.3,
        driftVz: (Math.random() - 0.5) * 0.2,
        radius: 24,
        isCurrent: true,
        createdAt: Date.now(),
        messages: [],
        artifacts: [],
      }
      dispatch({ type: 'ADD_ORB', payload: newOrb })
    }

    const startTime = Date.now()
    const result = await sendMessage(content, projectIdRef.current)
    const latency = Date.now() - startTime

    dispatch({ type: 'UPDATE_TECH_METRICS', payload: { tokenCountDelta: content.length, latency } })
    if (result?.project_id) {
      dispatch({ type: 'SET_PROJECT_ID', payload: result.project_id })
    }
    setTimeout(refreshStatusRef.current, 500)
  }, [sendMessage])

  useEffect(() => { handleSendRef.current = handleSend }, [handleSend])

  // Auto TTS
  const lastSpokenIdRef = useRef('')
  const lastVoiceUsedRef = useRef(false)
  useEffect(() => {
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant' && m.content)
    if (lastAssistant && lastAssistant.id !== lastSpokenIdRef.current && lastVoiceUsedRef.current) {
      lastSpokenIdRef.current = lastAssistant.id
      speak(lastAssistant.content)
      lastVoiceUsedRef.current = false
    }
  }, [messages, speak])

  const handleTanyinSubmit = useCallback(() => {
    const result = submitAnswers()
    if (result) {
      const answersText = result
        .map(r => `${r.label}: ${Array.isArray(r.value) ? r.value.join(', ') : r.value}`)
        .join('\n')
      handleSend(answersText)
    }
  }, [submitAnswers, handleSend])

  const handleOptionClick = useCallback((option: InteractiveOption) => {
    const content = option.type === 'fill' ? option.text : `${option.label}. ${option.text}`
    handleSend(content)
  }, [handleSend])

  // Voice visual mode
  const [voiceVisualLabel, setVoiceVisualLabel] = useState('墨滴涟漪')

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'KeyV' && !e.repeat && !e.ctrlKey && !e.metaKey) {
        const tag = (e.target as HTMLElement)?.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
        const mode = cycleVoiceVisualMode()
        const labels: Record<string, string> = {
          'ink-ripple': '墨滴涟漪',
          'liquid-wave': '液态波动',
          'silk-flow': '丝绒飘动',
          'heartbeat': '心跳脉冲',
        }
        setVoiceVisualLabel(labels[mode] || mode)
        return
      }
      if (e.code !== 'Space' || e.repeat) return
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      e.preventDefault()
      lastVoiceUsedRef.current = true
      startListening()
    }
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      e.preventDefault()
      stopListening()
    }
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [startListening, stopListening])

  return {
    messages, loading, loadingProgress, handleSend, handleOptionClick,
    voiceState, isVoiceMode: voiceState.isListening, voiceVisualLabel,
    tanyin, answers, textAnswers, closeTanyin, toggleOption, setRadioOption, setTextAnswer, handleTanyinSubmit,
    thinkingStartTime: thinkingStartRef.current,
    hitlInterrupt, clearHITL,
  }
}
