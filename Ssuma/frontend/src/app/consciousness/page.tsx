'use client'

import { useReducer, useCallback, useEffect, useRef } from 'react'
import dynamic from 'next/dynamic'
import type { PhaseInfo, PanelType, GradeLevel, TechMetrics, ProjectOrb } from './types/consciousness'
import { useTheme } from './hooks/useTheme'
import { useChatStream } from './hooks/useChatStream'
import { useVoiceMode } from './hooks/useVoiceMode'
import { useQuestionnaire } from './hooks/useQuestionnaire'
import { fetchFlowStatus, switchPhase, fetchLLMConfig, applyModelConfig } from '../../lib/api'
import { PHASE_LABELS } from '../../lib/constants'

import InkConversation from './components/ui/InkConversation'
import InputLine from './components/ui/InputLine'
import PhaseScroll from './components/ui/PhaseScroll'
import BrandPanel from './components/ui/BrandPanel'
import GradeOverlay from './components/ui/GradeOverlay'
import VoiceModeUI from './components/ui/VoiceMode'
import LoadingIndicator from './components/ui/LoadingIndicator'
import QuickActions from './components/ui/QuickActions'
import HistoryPanel from './components/panels/HistoryPanel'
import ArtifactPanel from './components/panels/ArtifactPanel'
import StudyPanel from './components/panels/StudyPanel'
import QuestionnaireModal from './components/modals/QuestionnaireModal'

const ConsciousnessScene = dynamic(
  () => import('./components/ConsciousnessScene'),
  { ssr: false }
)

const PHASE_KEYS = ['qishu', 'questionnaire', 'caiheng', 'zhenwei', 'ceshu', 'ningmo']

interface ConsciousnessState {
  projectId: string | null
  currentPhase: string
  phases: PhaseInfo[]
  artifacts: any[]
  llmConfig: any
  activePanel: PanelType
  grade: GradeLevel | null
  techMetrics: TechMetrics
  sessionTurns: number
  orbs: ProjectOrb[]
  selectedOrbId: string | null
}

type ConsciousnessAction =
  | { type: 'SET_PROJECT_ID'; payload: string | null }
  | { type: 'SET_CURRENT_PHASE'; payload: string }
  | { type: 'SET_PHASES'; payload: PhaseInfo[] }
  | { type: 'UPDATE_PHASE'; payload: { key: string; updates: Partial<PhaseInfo> } }
  | { type: 'SET_ARTIFACTS'; payload: any[] }
  | { type: 'SET_LLM_CONFIG'; payload: any }
  | { type: 'SET_ACTIVE_PANEL'; payload: PanelType }
  | { type: 'TOGGLE_ACTIVE_PANEL'; payload: PanelType }
  | { type: 'SET_GRADE'; payload: GradeLevel | null }
  | { type: 'UPDATE_TECH_METRICS'; payload: Partial<TechMetrics> & { tokenCountDelta?: number } }
  | { type: 'SET_SESSION_TURNS'; payload: number }
  | { type: 'ADD_ORB'; payload: ProjectOrb }
  | { type: 'UPDATE_ORB'; payload: { projectId: string; updates: Partial<ProjectOrb> } }
  | { type: 'SET_SELECTED_ORB_ID'; payload: string | null }
  | { type: 'UPDATE_STATUS'; payload: Record<string, any> }

const initialState: ConsciousnessState = {
  projectId: null,
  currentPhase: 'qishu',
  phases: [],
  artifacts: [],
  llmConfig: null,
  activePanel: null,
  grade: null,
  techMetrics: {
    tokenCount: 0,
    latency: 0,
    progress: 0,
  },
  sessionTurns: 0,
  orbs: [],
  selectedOrbId: null,
}

function consciousnessReducer(state: ConsciousnessState, action: ConsciousnessAction): ConsciousnessState {
  switch (action.type) {
    case 'SET_PROJECT_ID':
      return { ...state, projectId: action.payload }
    case 'SET_CURRENT_PHASE':
      return { ...state, currentPhase: action.payload }
    case 'SET_PHASES':
      return { ...state, phases: action.payload }
    case 'UPDATE_PHASE':
      return {
        ...state,
        phases: state.phases.map(p =>
          p.key === action.payload.key ? { ...p, ...action.payload.updates } : p
        ),
      }
    case 'SET_ARTIFACTS':
      return { ...state, artifacts: action.payload }
    case 'SET_LLM_CONFIG':
      return { ...state, llmConfig: action.payload }
    case 'SET_ACTIVE_PANEL':
      return { ...state, activePanel: action.payload }
    case 'TOGGLE_ACTIVE_PANEL':
      return { ...state, activePanel: state.activePanel === action.payload ? null : action.payload }
    case 'SET_GRADE':
      return { ...state, grade: action.payload }
    case 'UPDATE_TECH_METRICS': {
      const { tokenCountDelta, ...rest } = action.payload
      const newMetrics = { ...state.techMetrics, ...rest }
      if (tokenCountDelta !== undefined) {
        newMetrics.tokenCount = state.techMetrics.tokenCount + tokenCountDelta
      }
      return { ...state, techMetrics: newMetrics }
    }
    case 'SET_SESSION_TURNS':
      return { ...state, sessionTurns: action.payload }
    case 'ADD_ORB':
      return {
        ...state,
        orbs: [...state.orbs.map(o => ({ ...o, isCurrent: false })), action.payload],
        selectedOrbId: action.payload.id,
      }
    case 'UPDATE_ORB':
      return {
        ...state,
        orbs: state.orbs.map(o =>
          o.projectId === action.payload.projectId
            ? { ...o, ...action.payload.updates }
            : o
        ),
      }
    case 'SET_SELECTED_ORB_ID':
      return { ...state, selectedOrbId: action.payload }
    case 'UPDATE_STATUS': {
      const status = action.payload
      let gradeUpdate: Partial<ConsciousnessState> = {}
      if (status.completion_score !== undefined) {
        if (status.completion_score >= 0.9) gradeUpdate = { grade: 'supreme' }
        else if (status.completion_score >= 0.75) gradeUpdate = { grade: 'excellent' }
        else if (status.completion_score >= 0.6) gradeUpdate = { grade: 'good' }
        else if (status.completion_score > 0) gradeUpdate = { grade: 'pass' }
      }
      return {
        ...state,
        currentPhase: status.current_phase,
        artifacts: status.artifacts || [],
        sessionTurns: status.conversation_turns || 0,
        techMetrics: { ...state.techMetrics, progress: status.overall_progress || 0 },
        phases: state.phases.map(p => ({
          ...p,
          isCurrent: p.key === status.current_phase,
          isComplete: (status.phase_completion?.[p.key] || 0) >= 0.55,
          progress: Math.round((status.phase_completion?.[p.key] || 0) * 100),
        })),
        ...gradeUpdate,
      }
    }
    default:
      return state
  }
}

export default function ConsciousnessPage() {
  const [state, dispatch] = useReducer(consciousnessReducer, initialState)
  const { projectId, currentPhase, phases, artifacts, llmConfig, activePanel, grade, techMetrics, sessionTurns, orbs, selectedOrbId } = state

  const { theme, toggleTheme } = useTheme('xuanmo')
  const { messages, loading, loadingProgress, sendMessage } = useChatStream()
  const { voiceState, toggleListening } = useVoiceMode()
  const {
    questionnaire,
    answers,
    textAnswers,
    openQuestionnaire: _openQuestionnaire,
    closeQuestionnaire,
    toggleOption,
    setRadioOption,
    setTextAnswer,
    submitAnswers,
  } = useQuestionnaire()

  const hasCreatedOrbForProject = useRef<Set<string>>(new Set())
  const sessionOrbIdRef = useRef<string | null>(null)
  const thinkingStartRef = useRef<number>(0)

  useEffect(() => {
    if (loading) {
      if (thinkingStartRef.current === 0) {
        thinkingStartRef.current = Date.now()
      }
    } else {
      thinkingStartRef.current = 0
    }
  }, [loading])

  useEffect(() => {
    const initPhases: PhaseInfo[] = PHASE_KEYS.map(key => ({
      key: key as any,
      label: PHASE_LABELS[key]?.label || key,
      progress: 0,
      isCurrent: key === 'qishu',
      isComplete: false,
    }))
    dispatch({ type: 'SET_PHASES', payload: initPhases })
  }, [])

  useEffect(() => {
    fetchLLMConfig().then(config => dispatch({ type: 'SET_LLM_CONFIG', payload: config }))
  }, [])

  const refreshStatus = useCallback(async () => {
    if (!projectId) return
    const status = await fetchFlowStatus(projectId)
    if (status) {
      dispatch({ type: 'UPDATE_STATUS', payload: status })
    }
  }, [projectId])

  useEffect(() => {
    if (!projectId) return

    if (!hasCreatedOrbForProject.current.has(projectId)) {
      hasCreatedOrbForProject.current.add(projectId)

      const phaseLabel = PHASE_LABELS[currentPhase]?.label || currentPhase
      const newOrb: ProjectOrb = {
        id: `orb-${projectId}`,
        projectId,
        phase: currentPhase,
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
  }, [projectId, currentPhase])

  const orbMessagesRef = useRef(messages)
  const orbArtifactsRef = useRef(artifacts)
  useEffect(() => { orbMessagesRef.current = messages }, [messages])
  useEffect(() => { orbArtifactsRef.current = artifacts }, [artifacts])

  useEffect(() => {
    if (!projectId) return
    const currentMessages = orbMessagesRef.current
    const currentArtifacts = orbArtifactsRef.current
    dispatch({
      type: 'UPDATE_ORB',
      payload: {
        projectId,
        updates: {
          phase: currentPhase,
          phaseLabel: PHASE_LABELS[currentPhase]?.label || currentPhase,
          isCurrent: true,
          messages: [...currentMessages],
          artifacts: currentArtifacts.map((a: Record<string, unknown>) => String((a as Record<string, unknown>).name || (a as Record<string, unknown>).title || a)),
        },
      },
    })
  }, [projectId, currentPhase])

  const handleSend = useCallback(async (content: string) => {
    if (!sessionOrbIdRef.current) {
      const tempId = `orb-session-${Date.now()}`
      sessionOrbIdRef.current = tempId
      const phaseLabel = PHASE_LABELS[currentPhase]?.label || currentPhase
      const newOrb: ProjectOrb = {
        id: tempId,
        projectId: projectId || 'temp',
        phase: currentPhase,
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
    const result = await sendMessage(content, projectId)
    const latency = Date.now() - startTime

    dispatch({ type: 'UPDATE_TECH_METRICS', payload: { tokenCountDelta: content.length, latency } })

    if (result?.project_id) {
      dispatch({ type: 'SET_PROJECT_ID', payload: result.project_id })
    }

    setTimeout(refreshStatus, 500)
  }, [sendMessage, projectId, refreshStatus, currentPhase])

  const handlePhaseClick = useCallback(async (phaseKey: string) => {
    if (!projectId) return
    await switchPhase(projectId, phaseKey)
    await refreshStatus()
  }, [projectId, refreshStatus])

  const handlePanelClick = useCallback((type: PanelType) => {
    dispatch({ type: 'TOGGLE_ACTIVE_PANEL', payload: type })
  }, [])

  const handleApplyConfig = useCallback(async (config: any) => {
    const result = await applyModelConfig(config)
    if (result) {
      const newConfig = await fetchLLMConfig()
      dispatch({ type: 'SET_LLM_CONFIG', payload: newConfig })
    }
  }, [])

  const handleQuestionnaireSubmit = useCallback(() => {
    const result = submitAnswers()
    if (result) {
      const answersText = result
        .map(r => `${r.label}: ${Array.isArray(r.value) ? r.value.join(', ') : r.value}`)
        .join('\n')
      handleSend(answersText)
    }
  }, [submitAnswers, handleSend])

  const handleOrbClick = useCallback((orbId: string) => {
    dispatch({ type: 'SET_SELECTED_ORB_ID', payload: orbId })
    dispatch({ type: 'SET_ACTIVE_PANEL', payload: 'history' })
  }, [])

  useEffect(() => {
    if (grade) {
      const timer = setTimeout(() => dispatch({ type: 'SET_GRADE', payload: null }), 4000)
      return () => clearTimeout(timer)
    }
  }, [grade])

  const isVoiceMode = voiceState.isListening

  const selectedOrb = orbs.find(o => o.id === selectedOrbId) || null
  const artifactNames = artifacts.map((a: any) => a.name || a.title || String(a))

  return (
    <div className="consciousness-space">
      <ConsciousnessScene
        currentPhase={currentPhase}
        voiceAmplitude={voiceState.amplitude}
        theme={theme}
        isThinking={loading}
        orbs={orbs}
        onOrbClick={handleOrbClick}
      />

      <div className="ui-overlay">
        <InkConversation messages={messages} isThinking={loading} thinkingStartTime={thinkingStartRef.current} />

        <PhaseScroll
          phases={phases}
          onPhaseClick={handlePhaseClick}
          isVoiceMode={isVoiceMode}
        />

        <InputLine
          onSend={handleSend}
          onVoiceToggle={toggleListening}
          isVoiceMode={isVoiceMode}
          disabled={loading}
        />

        <LoadingIndicator loading={loading} progress={loadingProgress} />

        <QuickActions
          loading={loading}
          progress={loadingProgress}
          isVoiceMode={isVoiceMode}
        />

        <BrandPanel
          onLinkClick={handlePanelClick}
          techMetrics={techMetrics}
          sessionTurns={sessionTurns}
          isVoiceMode={isVoiceMode}
        />

        <GradeOverlay grade={grade} />

        <VoiceModeUI
          voiceState={voiceState}
          onToggle={toggleListening}
        />

        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'xuanmo' ? '墨' : '纸'}
        </button>

        {activePanel === 'history' && (
          <HistoryPanel
            messages={selectedOrb?.messages || messages}
            artifacts={selectedOrb?.artifacts || artifactNames}
            orb={selectedOrb}
            allOrbs={orbs}
            onClose={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
            onOrbSelect={(orbId) => dispatch({ type: 'SET_SELECTED_ORB_ID', payload: orbId })}
          />
        )}

        {activePanel === 'artifact' && (
          <ArtifactPanel
            artifacts={artifacts}
            onClose={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
          />
        )}

        {activePanel === 'study' && (
          <StudyPanel
            config={llmConfig}
            onClose={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
            onApply={handleApplyConfig}
          />
        )}

        {questionnaire && (
          <QuestionnaireModal
            questionnaire={questionnaire}
            answers={answers}
            textAnswers={textAnswers}
            onToggleOption={toggleOption}
            onSetRadio={setRadioOption}
            onSetText={setTextAnswer}
            onSubmit={handleQuestionnaireSubmit}
            onClose={closeQuestionnaire}
          />
        )}
      </div>
    </div>
  )
}
