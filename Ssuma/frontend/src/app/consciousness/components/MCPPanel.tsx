'use client'

import { useState, useEffect, useRef } from 'react'
import { fetchMCPStatus, fetchMCPTools } from '../../../lib/api'
import type { MCPStatus, MCPTool } from '../../../lib/api'

interface Props {
  className?: string
}

export default function MCPPanel({ className }: Props) {
  const [status, setStatus] = useState<MCPStatus | null>(null)
  const [tools, setTools] = useState<MCPTool[]>([])
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(true)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    Promise.all([fetchMCPStatus(), fetchMCPTools()])
      .then(([statusResult, toolsResult]) => {
        if (!mountedRef.current) return
        setStatus(statusResult)
        if (toolsResult) setTools(toolsResult.tools)
      })
      .finally(() => {
        if (mountedRef.current) setLoading(false)
      })
    return () => {
      mountedRef.current = false
    }
  }, [])

  const handleRefresh = () => {
    setLoading(true)
    Promise.all([fetchMCPStatus(), fetchMCPTools()])
      .then(([statusResult, toolsResult]) => {
        setStatus(statusResult)
        if (toolsResult) setTools(toolsResult.tools)
      })
      .finally(() => setLoading(false))
  }

  const connectedCount = status?.servers.filter((s) => s.status === 'connected').length ?? 0
  const totalServers = status?.servers.length ?? 0

  return (
    <div
      className={`bg-black/60 backdrop-blur-md border border-ink/20 rounded-sm p-4 max-w-sm w-full font-[var(--font-serif)] ${className ?? ''}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-ink-light text-[10px] font-light tracking-[0.3em] uppercase">
            MCP 服务
          </span>
          {status && (
            <span className="text-ink/40 text-[9px] font-light tracking-wider">
              {connectedCount}/{totalServers} 已连接
            </span>
          )}
        </div>
        <button
          className="text-ink/50 hover:text-ink-light text-[11px] transition-colors disabled:opacity-30"
          onClick={handleRefresh}
          disabled={loading}
          title="刷新"
        >
          {loading ? '...' : '↻'}
        </button>
      </div>

      {/* Server List */}
      <div className="space-y-1.5 mb-3">
        {status?.servers.map((server) => (
          <div
            key={server.name}
            className="flex items-center justify-between py-1"
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  server.status === 'connected'
                    ? 'bg-[var(--mountain-green)]'
                    : server.status === 'error'
                      ? 'bg-[var(--seal-red)]'
                      : 'bg-ink/30'
                }`}
              />
              <span className="text-ink/80 text-[12px]">{server.name}</span>
            </div>
            <span className="text-ink/40 text-[9px] tracking-wider">
              {server.tools_count} 工具
            </span>
          </div>
        ))}

        {!status && (
          <div className="text-ink/30 text-[11px] text-center py-4">
            {loading ? '加载中...' : '无法获取 MCP 状态'}
          </div>
        )}

        {status && totalServers === 0 && (
          <div className="text-ink/30 text-[11px] text-center py-4">
            暂无已连接的服务
          </div>
        )}
      </div>

      {/* Tools Count & Expand Toggle */}
      {tools.length > 0 && (
        <>
          <div
            className="flex items-center justify-between py-2 border-t border-ink/10 cursor-pointer group"
            onClick={() => setExpanded(!expanded)}
          >
            <span className="text-ink/50 text-[10px] tracking-[0.15em]">
              可用工具 ({tools.length})
            </span>
            <span className="text-ink/40 text-[10px] group-hover:text-ink-light transition-colors">
              {expanded ? '收起' : '展开'}
            </span>
          </div>

          {/* Expandable Tool List */}
          {expanded && (
            <div className="mt-2 max-h-48 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
              {tools.map((tool) => (
                <div
                  key={`${tool.server}-${tool.name}`}
                  className="bg-ink/5 border border-ink/8 rounded-sm p-2"
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-ink-light text-[11px] font-medium">
                      {tool.name}
                    </span>
                    <span className="text-ink/30 text-[8px] bg-ink/8 px-1.5 py-0.5 rounded-sm">
                      {tool.server}
                    </span>
                  </div>
                  {tool.description && (
                    <div className="text-ink/50 text-[10px] leading-relaxed line-clamp-2">
                      {tool.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
