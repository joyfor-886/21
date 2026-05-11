import { API_BASE } from "./constants"
import type { FlowStatus, LLMConfig, FetchedModel } from "./types"

export async function fetchFlowStatus(projectId: string): Promise<FlowStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/status/${projectId}`)
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export async function sendFlowChat(
  projectId: string | null,
  message: string
): Promise<{ response?: string; project_id?: string; [key: string]: any } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId || "", message }),
    })
    if (!res.ok) throw new Error(`Error: ${res.status}`)
    return await res.json()
  } catch (e: any) {
    return { response: `Error: ${e.message}` }
  }
}

export async function switchPhase(projectId: string, phase: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/switch/${projectId}?workflow=${phase}`, {
      method: "POST",
    })
    return res.ok
  } catch {
    return false
  }
}

export async function resetFlow(projectId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/reset/${projectId}`, { method: "POST" })
    return res.ok
  } catch {
    return false
  }
}

export async function fetchLLMConfig(): Promise<LLMConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/config`)
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export async function fetchProviders(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/list-providers`)
    if (res.ok) {
      const data = await res.json()
      return data.providers || []
    }
    return []
  } catch {
    return []
  }
}

export async function fetchModels(
  providerType: string,
  baseUrl: string,
  apiKey?: string
): Promise<{ success: boolean; models?: FetchedModel[]; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/fetch-models`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider_type: providerType,
        base_url: baseUrl,
        api_key: apiKey || undefined,
      }),
    })
    if (res.ok) {
      const data = await res.json()
      return data
    }
    return { success: false, error: `请求失败: ${res.status}` }
  } catch (e: any) {
    return { success: false, error: e.message || "连接失败" }
  }
}

export async function applyModelConfig(config: {
  mode: string
  chat_provider: string
  chat_model: string
  base_url?: string
  api_key?: string
}): Promise<{ success: boolean; [key: string]: any } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/apply-model`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}
