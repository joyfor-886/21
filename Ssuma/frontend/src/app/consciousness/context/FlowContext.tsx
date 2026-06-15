'use client'

import { createContext, useContext, useReducer, useCallback, useEffect, useRef, type ReactNode } from 'react'
import type { PhaseInfo, PanelType, GradeLevel, TechMetrics, ProjectOrb } from '../types/consciousness'
import type { ArtifactSummary, LLMConfig, ApplyModelConfigRequest, AutoPilotResult, FlowStatus, HITLInterrupt } from '../../../lib/types'
import { fetchFlowStatus, switchPhase, fetchLLMConfig, applyModelConfig, exportIDEFiles, runAutoPilot, downloadFilesAsZip, submitHITLFeedback } from '../../../lib/api'
import { PHASE_LABELS } from '../../../lib/constants'

const PHASE_KEYS = ['qishu', 'tanyin', 'caiheng', 'zhenwei', 'ceshu', 'ningmo']

interface FlowState {
  projectId: string | null
  currentPhase: string
  phases: PhaseInfo[]
  artifacts: ArtifactSummary[]
  llmConfig: LLMConfig | null
  activePanel: PanelType
  grade: GradeLevel | null
  techMetrics: TechMetrics
  sessionTurns: number
  orbs: ProjectOrb[]
  selectedOrbId: string | null
  complexity: string
  complexityLabel: string
  canExport: boolean
  hitlInterrupt: HITLInterrupt | null
}

type FlowAction =
  | { type: 'SET_PROJECT_ID'; payload: string | null }
  | { type: 'SET_CURRENT_PHASE'; payload: string }
  | { type: 'SET_PHASES'; payload: PhaseInfo[] }
  | { type: 'UPDATE_PHASE'; payload: { key: string; updates: Partial<PhaseInfo> } }
  | { type: 'SET_ARTIFACTS'; payload: ArtifactSummary[] }
  | { type: 'SET_LLM_CONFIG'; payload: LLMConfig | null }
  | { type: 'SET_ACTIVE_PANEL'; payload: PanelType }
  | { type: 'TOGGLE_ACTIVE_PANEL'; payload: PanelType }
  | { type: 'SET_GRADE'; payload: GradeLevel | null }
  | { type: 'UPDATE_TECH_METRICS'; payload: Partial<TechMetrics> & { tokenCountDelta?: number } }
  | { type: 'SET_SESSION_TURNS'; payload: number }
  | { type: 'ADD_ORB'; payload: ProjectOrb }
  | { type: 'UPDATE_ORB'; payload: { projectId: string; updates: Partial<ProjectOrb> } }
  | { type: 'SET_SELECTED_ORB_ID'; payload: string | null }
  | { type: 'UPDATE_STATUS'; payload: FlowStatus }
  | { type: 'SET_HITL_INTERRUPT'; payload: HITLInterrupt | null }

const initialState: FlowState = {
  projectId: null,
  currentPhase: 'qishu',
  phases: [],
  artifacts: [],
  llmConfig: null,
  activePanel: null,
  grade: null,
  techMetrics: { tokenCount: 0, latency: 0, progress: 0 },
  sessionTurns: 0,
  orbs: [],
  selectedOrbId: null,
  complexity: '',
  complexityLabel: '',
  canExport: false,
  hitlInterrupt: null,
}

function flowReducer(state: FlowState, action: FlowAction): FlowState {
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
    case 'SET_HITL_INTERRUPT':
      return { ...state, hitlInterrupt: action.payload }
    case 'UPDATE_STATUS': {
      const status = action.payload
      let gradeUpdate: Partial<FlowState> = {}
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
        complexity: status.complexity || '',
        complexityLabel: status.complexity_label || '',
        canExport: status.can_export || false,
        ...gradeUpdate,
      }
    }
    default:
      return state
  }
}

interface FlowContextValue {
  state: FlowState
  dispatch: React.Dispatch<FlowAction>
  refreshStatus: () => Promise<void>
  handlePhaseClick: (phaseKey: string) => Promise<void>
  handlePanelClick: (type: PanelType) => void
  handleApplyConfig: (config: ApplyModelConfigRequest) => Promise<void>
  handleOrbClick: (orbId: string) => void
  handleExport: () => Promise<void>
  handleAutoPilot: (message: string, channel?: string) => Promise<AutoPilotResult | null>
  handleHITLResponse: (responseType: "accept" | "ignore" | "response" | "edit", content?: string) => Promise<void>
}

const FlowContext = createContext<FlowContextValue | null>(null)

export function FlowProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(flowReducer, initialState)
  const hasCreatedOrbForProject = useRef<Set<string>>(new Set())

  useEffect(() => {
    const initPhases: PhaseInfo[] = PHASE_KEYS.map(key => ({
      key: key as PhaseInfo['key'],
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
    if (!state.projectId) return
    const status = await fetchFlowStatus(state.projectId)
    if (status) {
      dispatch({ type: 'UPDATE_STATUS', payload: status })
    }
  }, [state.projectId])

  useEffect(() => {
    if (!state.projectId) return
    if (!hasCreatedOrbForProject.current.has(state.projectId)) {
      hasCreatedOrbForProject.current.add(state.projectId)
      const phaseLabel = PHASE_LABELS[state.currentPhase]?.label || state.currentPhase
      const newOrb: ProjectOrb = {
        id: `orb-${state.projectId}`,
        projectId: state.projectId,
        phase: state.currentPhase,
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
  }, [state.projectId, state.currentPhase])

  useEffect(() => {
    if (state.grade) {
      const timer = setTimeout(() => dispatch({ type: 'SET_GRADE', payload: null }), 4000)
      return () => clearTimeout(timer)
    }
  }, [state.grade])

  const handlePhaseClick = useCallback(async (phaseKey: string) => {
    if (!state.projectId) return
    await switchPhase(state.projectId, phaseKey)
    await refreshStatus()
  }, [state.projectId, refreshStatus])

  const handlePanelClick = useCallback((type: PanelType) => {
    dispatch({ type: 'TOGGLE_ACTIVE_PANEL', payload: type })
  }, [])

  const handleApplyConfig = useCallback(async (config: ApplyModelConfigRequest) => {
    const result = await applyModelConfig(config)
    if (result) {
      const newConfig = await fetchLLMConfig()
      dispatch({ type: 'SET_LLM_CONFIG', payload: newConfig })
    }
  }, [])

  const handleOrbClick = useCallback((orbId: string) => {
    dispatch({ type: 'SET_SELECTED_ORB_ID', payload: orbId })
    dispatch({ type: 'SET_ACTIVE_PANEL', payload: 'history' })
  }, [])

  const handleExport = useCallback(async () => {
    if (!state.projectId) return
    const result = await exportIDEFiles(state.projectId)
    if (result?.files) {
      const count = downloadFilesAsZip(result.files, result.project_name || state.projectId)
      dispatch({ type: 'SET_GRADE', payload: 'excellent' })
    }
  }, [state.projectId])

  const handleAutoPilot = useCallback(async (message: string, channel: string = "standard") => {
    if (!state.projectId && !message) return null
    const pid = state.projectId || `proj-${Date.now()}`
    if (!state.projectId) {
      dispatch({ type: 'SET_PROJECT_ID', payload: pid })
    }
    const result = await runAutoPilot(pid, message, channel)
    if (result?.success) {
      dispatch({ type: 'UPDATE_STATUS', payload: {
        current_phase: 'ningmo',
        current_phase_label: 'Ningmo',
        channel: 'standard',
        channel_phases: [],
        overall_progress: 100,
        completion_score: result.quality_score || 0.9,
        conversation_turns: 6,
        should_remind: false,
        suggested_next: 'completed',
        can_export: true,
        artifacts: [],
        phase_completion: { qishu: 1, caiheng: 1, zhenwei: 1, ceshu: 1, ningmo: 1, powang: 1 },
      }})
      if (result.ide_files) {
        downloadFilesAsZip(result.ide_files, result.project_id)
      }
    }
    return result
  }, [state.projectId])

  const handleHITLResponse = useCallback(async (responseType: "accept" | "ignore" | "response" | "edit", content?: string) => {
    if (!state.projectId) return
    const result = await submitHITLFeedback(state.projectId, responseType, content)
    if (result.success) {
      dispatch({ type: 'SET_HITL_INTERRUPT', payload: null })
      // 如果有反馈消息，需要注入到对话中
      if (result.inject_message) {
        // 由 useConsciousness hook 处理注入
      }
    }
  }, [state.projectId])

  return (
    <FlowContext.Provider value={{ state, dispatch, refreshStatus, handlePhaseClick, handlePanelClick, handleApplyConfig, handleOrbClick, handleExport, handleAutoPilot, handleHITLResponse }}>
      {children}
    </FlowContext.Provider>
  )
}

export function useFlowContext() {
  const context = useContext(FlowContext)
  if (!context) {
    throw new Error('useFlowContext must be used within a FlowProvider')
  }
  return context
}