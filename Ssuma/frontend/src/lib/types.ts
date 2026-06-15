export interface Message {
  role: "user" | "assistant"
  content: string
}

export interface ArtifactSummary {
  phase: string
  summary: string
  decisions_count: number
  open_questions_count: number
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
  complexity?: string
  complexity_label?: string
  can_export?: boolean
  artifacts: ArtifactSummary[]
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

export interface ApplyModelConfigRequest {
  mode: string
  chat_provider: string
  chat_model: string
  base_url?: string
  api_key?: string
}

export interface FlowChatResponse {
  project_id: string
  response: string
  current_phase: string
  current_phase_label: string
  intent_analysis: {
    intent: string
    clarity: string
    confidence?: number
  }
  suggested_next_phase?: string
  suggested_next_action?: string
  workflow_options: Array<{
    id: string
    label: string
    description: string
    icon: string
  }>
  completed: boolean
  hitl_interrupt?: HITLInterrupt | null
}

export interface AutoPilotResult {
  success: boolean
  project_id: string
  final_spec: string
  file_count: number
  ide_files: Record<string, string>
  phase_summary: Array<{ phase: string; duration_seconds: number }>
  total_duration_seconds: number
  quality_score: number | null
}

export interface ModelTierInfo {
  tier: string
  label: string
  color: string
  capability_config?: Record<string, unknown>
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

// HITL (Human-in-the-Loop) types
export interface HITLInterrupt {
  id: string
  phase: string
  reason: string
  content: string
  options: string[]
  status: "pending" | "responded" | "expired"
}

export interface HITLConfig {
  phases: Record<string, boolean>
  mcp_tool_approval: boolean
  completion_threshold: number
  timeout_seconds: number
}

export interface HITLResponse {
  success: boolean
  action?: "continue" | "skip" | "feedback" | "edit"
  message?: string
  feedback?: string
  edited_content?: string
  inject_message?: string
  error?: string
}
