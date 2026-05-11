export type Theme = 'xuanmo' | 'xuanzhi'

export type GradeLevel = 'supreme' | 'excellent' | 'good' | 'pass'

export type PhaseKey = 'qishu' | 'questionnaire' | 'caiheng' | 'zhenwei' | 'ceshu' | 'ningmo'

export interface InkMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface PhaseInfo {
  key: PhaseKey
  label: string
  progress: number
  isCurrent: boolean
  isComplete: boolean
}

export interface QuestionnaireItem {
  type: 'checkbox' | 'radio' | 'text'
  label: string
  options?: string[]
  placeholder?: string
  required?: boolean
}

export interface Questionnaire {
  title: string
  items: QuestionnaireItem[]
}

export interface TechMetrics {
  tokenCount: number
  latency: number
  progress: number
}

export interface VoiceState {
  isListening: boolean
  amplitude: number
  transcript: string
}

export type PanelType = 'history' | 'artifact' | 'study' | null

export interface ProjectOrb {
  id: string
  projectId: string
  phase: string
  phaseLabel: string
  x: number
  z: number
  driftVx: number
  driftVz: number
  radius: number
  isCurrent: boolean
  createdAt: number
  messages: InkMessage[]
  artifacts: string[]
}

export const PHASE_COLORS: Record<string, { r: number; g: number; b: number; hex: string }> = {
  qishu: { r: 100, g: 140, b: 200, hex: '#648cc8' },
  questionnaire: { r: 80, g: 170, b: 160, hex: '#50aaa0' },
  caiheng: { r: 140, g: 100, b: 180, hex: '#8c64b4' },
  zhenwei: { r: 80, g: 160, b: 100, hex: '#50a064' },
  ceshu: { r: 180, g: 130, b: 70, hex: '#b48246' },
  powang: { r: 160, g: 90, b: 90, hex: '#a05a5a' },
  jianyan: { r: 100, g: 170, b: 130, hex: '#64aa82' },
  ningmo: { r: 212, g: 168, b: 67, hex: '#d4a843' },
  completed: { r: 212, g: 168, b: 67, hex: '#d4a843' },
  intent_detection: { r: 120, g: 120, b: 180, hex: '#7878b4' },
}
