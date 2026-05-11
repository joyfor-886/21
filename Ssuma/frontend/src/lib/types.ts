export interface Message {
  role: "user" | "assistant"
  content: string
}

export interface FlowStatus {
  current_phase: string
  current_phase_label: string
  channel: string
  channel_phases: string[]
  overall_progress: number
  completion_score: number
  phase_completion: Record<string, number>
  conversation_turns: number
  should_remind: boolean
  suggested_next: string
  artifacts: Array<{
    phase: string
    summary: string
    decisions_count: number
    open_questions_count: number
  }>
}

export interface LLMConfig {
  mode: string
  chat_model: {
    provider: string
    model: string
    base_url?: string
    api_key?: string
    tier?: string
  }
  generate_model?: {
    provider: string
    model: string
  }
  current_tier?: string
  current_tier_label?: string
}

export interface ModelTierInfo {
  tier: string
  label: string
  color: string
  capability_config?: Record<string, any>
}

export interface FetchedModel {
  name: string
  architecture: string
  quantization: string
  size: number
  size_label: string
  parameter_size: string
  family: string
  format: string
}
