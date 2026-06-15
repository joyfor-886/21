import { API_BASE } from "./constants"
import type { FlowStatus, LLMConfig, FetchedModel, FlowChatResponse, ApplyModelConfigRequest, AutoPilotResult, HITLInterrupt, HITLConfig, HITLResponse } from "./types"

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (typeof window !== "undefined") {
    const apiKey = localStorage.getItem("ssuma_api_key") || ""
    if (apiKey) {
      headers["X-API-Key"] = apiKey
    }
  }
  return headers
}

export async function fetchFlowStatus(projectId: string): Promise<FlowStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/status/${projectId}`, {
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export async function sendFlowChat(
  projectId: string | null,
  message: string
): Promise<FlowChatResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/chat`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ project_id: projectId || "", message }),
    })
    if (!res.ok) throw new Error(`Error: ${res.status}`)
    return await res.json()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Unknown error"
    return { response: `Error: ${msg}` } as unknown as FlowChatResponse
  }
}

export async function switchPhase(projectId: string, phase: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/switch/${projectId}?workflow=${phase}`, {
      method: "POST",
      headers: getAuthHeaders(),
    })
    return res.ok
  } catch {
    return false
  }
}

export async function resetFlow(projectId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/reset/${projectId}`, {
      method: "POST",
      headers: getAuthHeaders(),
    })
    return res.ok
  } catch {
    return false
  }
}

export async function fetchLLMConfig(): Promise<LLMConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/config`, {
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export async function fetchProviders(): Promise<Array<{ name: string; model: string; base_url?: string; type?: string }>> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/list-providers`, {
      headers: getAuthHeaders(),
    })
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
      headers: getAuthHeaders(),
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
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "连接失败"
    return { success: false, error: msg }
  }
}

export async function exportIDEFiles(projectId: string): Promise<{
  success: boolean
  project_name: string
  complexity: string
  complexity_label: string
  file_count: number
  files: Record<string, string>
} | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/flow/export/${projectId}`, {
      method: "POST",
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export async function runAutoPilot(
  projectId: string,
  message: string,
  channel: string = "standard"
): Promise<AutoPilotResult | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/flow/autopilot/${projectId}?message=${encodeURIComponent(message)}&channel=${channel}`,
      { method: "POST", headers: getAuthHeaders() }
    )
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export function createAutoPilotStreamUrl(projectId: string, message: string, channel: string = "standard"): string {
  return `${API_BASE}/api/v1/flow/autopilot/stream/${projectId}?message=${encodeURIComponent(message)}&channel=${channel}`
}

export function downloadFilesAsZip(files: Record<string, string>, projectName: string) {
  // 使用 JSZip 或简单的逐个下载
  // 这里采用逐个文件的文本下载方式
  const total = Object.keys(files).length
  let downloaded = 0
  for (const [path, content] of Object.entries(files)) {
    setTimeout(() => {
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${projectName}/${path}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      downloaded++
    }, downloaded * 200) // 错开下载，避免浏览器拦截
  }
  return total
}

export async function applyModelConfig(config: ApplyModelConfigRequest): Promise<{ success: boolean; [key: string]: unknown } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/llm/apply-model`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(config),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

// ===== HITL (Human-in-the-Loop) APIs =====

export async function fetchPendingInterrupt(projectId: string): Promise<{ pending: boolean; interrupt: HITLInterrupt | null }> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/hitl/pending/${projectId}`, {
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return { pending: false, interrupt: null }
  } catch {
    return { pending: false, interrupt: null }
  }
}

export async function respondToInterrupt(interruptId: string, responseType: "accept" | "ignore" | "response" | "edit", content?: string): Promise<HITLResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/hitl/respond/${interruptId}`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ response_type: responseType, content }),
    })
    if (res.ok) return await res.json()
    return { success: false, error: "Request failed" }
  } catch (e) {
    return { success: false, error: String(e) }
  }
}

export async function submitHITLFeedback(projectId: string, responseType: "accept" | "ignore" | "response" | "edit", content?: string): Promise<HITLResponse & { inject_message?: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/hitl/feedback/${projectId}`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ response_type: responseType, content }),
    })
    if (res.ok) return await res.json()
    return { success: false, error: "Request failed" }
  } catch (e) {
    return { success: false, error: String(e) }
  }
}

export async function fetchHITLConfig(): Promise<HITLConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/hitl/config`, {
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

// ===== MCP (Model Context Protocol) APIs =====

export interface MCPStatus {
  connected: boolean
  servers: Array<{
    name: string
    status: "connected" | "disconnected" | "error"
    tools_count: number
  }>
  tools_count: number
}

export interface MCPTool {
  name: string
  description: string
  server: string
}

export async function fetchMCPStatus(): Promise<MCPStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/mcp/status`, {
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}

export async function fetchMCPTools(server?: string): Promise<{ tools: MCPTool[] } | null> {
  try {
    const url = server
      ? `${API_BASE}/api/v1/mcp/tools?server=${encodeURIComponent(server)}`
      : `${API_BASE}/api/v1/mcp/tools`
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    })
    if (res.ok) return await res.json()
    return null
  } catch {
    return null
  }
}
