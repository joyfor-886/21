'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import type { InkMessage } from '../types/consciousness'
import type { HITLInterrupt } from '../../../lib/types'
import { sendFlowChat } from '../../../lib/api'

export function useChatStream() {
  const [messages, setMessages] = useState<InkMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [hitlInterrupt, setHitlInterrupt] = useState<HITLInterrupt | null>(null)
  const mountedRef = useRef(true)
  const sendingRef = useRef(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const sendMessage = useCallback(async (
    content: string,
    projectId: string | null
  ): Promise<{ response: string; project_id?: string } | null> => {
    if (!content?.trim() || sendingRef.current) return null

    const trimmedContent = content.trim()
    sendingRef.current = true

    const userMsg: InkMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: trimmedContent,
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
    setLoading(true)
    setLoadingProgress(10)

    try {
      const data = await sendFlowChat(projectId, trimmedContent)

      if (!data) throw new Error('No response from server')

      const aiContent = data.response || ''
      const returnedProjectId = data.project_id

      if (mountedRef.current) {
        const interactiveOptions = (data.workflow_options || []).map(
          (opt: { id: string; label: string; description: string }) => ({
            label: opt.label || opt.id,
            text: opt.description || opt.label,
          })
        )

        // 处理 HITL 中断
        if (data.hitl_interrupt) {
          setHitlInterrupt(data.hitl_interrupt as HITLInterrupt)
        }

        setMessages(prev =>
          prev.map(m => m.id === aiMsgId ? {
            ...m,
            content: aiContent,
            interactiveOptions,
          } : m)
        )
        setLoadingProgress(100)
        setTimeout(() => {
          if (mountedRef.current) {
            setLoading(false)
            setLoadingProgress(0)
          }
        }, 300)
      }

      sendingRef.current = false
      return { response: aiContent, project_id: returnedProjectId }

    } catch (err: unknown) {
      sendingRef.current = false

      if (!mountedRef.current) return null

      setLoading(false)
      setLoadingProgress(0)

      const msg = err instanceof Error ? err.message : '未知错误'
      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: `⚠ ${msg}`,
        timestamp: Date.now(),
      }])

      return null
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setHitlInterrupt(null)
  }, [])

  const clearHITL = useCallback(() => setHitlInterrupt(null), [])

  const abort = useCallback(() => {
    sendingRef.current = false
    setLoading(false)
    setLoadingProgress(0)
  }, [])

  return { messages, loading, loadingProgress, hitlInterrupt, sendMessage, clearMessages, clearHITL, abort }
}
