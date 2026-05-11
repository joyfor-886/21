'use client'

import { useState, useCallback, useRef } from 'react'
import type { InkMessage } from '../types/consciousness'
import { API_BASE } from '../../../lib/constants'

export function useChatStream() {
  const [messages, setMessages] = useState<InkMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(0)
  const abortRef = useRef<AbortController | null>(null)
  const loadingRef = useRef(false)

  const sendMessage = useCallback(async (
    content: string,
    projectId: string | null
  ) => {
    if (!content.trim() || loadingRef.current) return null

    abortRef.current?.abort()

    const userMsg: InkMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    }

    const aiMsgId = `a-${Date.now()}`
    const aiMsg: InkMessage = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }

    setMessages(prev => [...prev, userMsg, aiMsg])
    loadingRef.current = true
    setLoading(true)
    setLoadingProgress(10)

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const res = await fetch(`${API_BASE}/api/v1/flow/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId || '', message: content.trim() }),
        signal: abortController.signal,
      })

      if (!res.ok) throw new Error(`Error: ${res.status}`)
      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      let returnedProjectId: string | undefined

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data:')) continue

          const jsonStr = trimmed.slice(5).trim()
          if (!jsonStr) continue

          let parsed: any
          try {
            parsed = JSON.parse(jsonStr)
          } catch {
            continue
          }

          if (parsed.content) {
            accumulated += parsed.content
            const currentContent = accumulated
            setMessages(prev =>
              prev.map(m => m.id === aiMsgId ? { ...m, content: currentContent } : m)
            )
            setLoadingProgress(prev => Math.min(prev + 2, 90))
          }

          if (parsed.done) {
            setLoadingProgress(100)
            if (parsed.project_id) {
              returnedProjectId = parsed.project_id
            }
          }
        }
      }

      loadingRef.current = false
      setLoading(false)
      setLoadingProgress(0)
      return { response: accumulated, project_id: returnedProjectId }
    } catch (e: any) {
      loadingRef.current = false
      setLoading(false)
      setLoadingProgress(0)
      if (e.name !== 'AbortError') {
        const errMsg: InkMessage = {
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: `连接异常：${e.message}`,
          timestamp: Date.now(),
        }
        setMessages(prev => [...prev, errMsg])
      }
      return null
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    loadingRef.current = false
    setLoading(false)
    setLoadingProgress(0)
  }, [])

  return { messages, loading, loadingProgress, sendMessage, clearMessages, abort }
}
