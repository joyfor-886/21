'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { InkMessage, InteractiveOption } from '../../types/consciousness'

interface Props {
  messages: InkMessage[]
  isThinking?: boolean
  thinkingStartTime?: number
  onOptionClick?: (option: InteractiveOption) => void
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  return `${h}:${m}`
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const remainSec = sec % 60
  return `${min}m${remainSec}s`
}

function InteractiveOptions({ options, onOptionClick }: { options: InteractiveOption[]; onOptionClick: (opt: InteractiveOption) => void }) {
  const [fillValue, setFillValue] = useState('')
  const fillRef = useRef<HTMLInputElement>(null)

  const hasFill = options.some(o => o.type === 'fill')
  const choiceOptions = options.filter(o => o.type !== 'fill')

  const handleFillSubmit = useCallback(() => {
    if (fillValue.trim()) {
      onOptionClick({ label: 'fill', text: fillValue.trim(), type: 'fill' })
      setFillValue('')
    }
  }, [fillValue, onOptionClick])

  return (
    <div className="interactive-options">
      {choiceOptions.length > 0 && (
        <div className="option-chips">
          {choiceOptions.map((opt, i) => (
            <button
              key={i}
              className="option-chip"
              onClick={() => onOptionClick(opt)}
            >
              <span className="option-chip-label">{opt.label}</span>
              <span className="option-chip-text">{opt.text}</span>
            </button>
          ))}
        </div>
      )}
      {hasFill && (
        <div className="option-fill">
          <input
            ref={fillRef}
            type="text"
            className="option-fill-input"
            value={fillValue}
            onChange={e => setFillValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleFillSubmit() }}
            placeholder="输入你的回答..."
          />
          <button className="option-fill-submit" onClick={handleFillSubmit}>→</button>
        </div>
      )}
    </div>
  )
}

export default function InkConversation({ messages, isThinking = false, thinkingStartTime, onOptionClick }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [displayMessages, setDisplayMessages] = useState<InkMessage[]>([])
  const [thinkingDuration, setThinkingDuration] = useState<number>(0)
  const thinkTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    setDisplayMessages(prev => {
      const merged = [...prev]
      for (const msg of messages) {
        const existingIdx = merged.findIndex(m => m.id === msg.id)
        if (existingIdx === -1) {
          merged.push(msg)
        } else if (msg.content !== merged[existingIdx].content) {
          merged[existingIdx] = msg
        }
      }
      return merged
    })
  }, [messages])

  useEffect(() => {
    if (scrollRef.current) {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
      })
    }
  }, [displayMessages, isThinking])

  useEffect(() => {
    if (isThinking && thinkingStartTime) {
      setThinkingDuration(0)
      thinkTimerRef.current = setInterval(() => {
        setThinkingDuration(Date.now() - thinkingStartTime)
      }, 100)
    } else {
      if (thinkTimerRef.current) {
        clearInterval(thinkTimerRef.current)
        thinkTimerRef.current = null
      }
      setThinkingDuration(0)
    }
    return () => {
      if (thinkTimerRef.current) clearInterval(thinkTimerRef.current)
    }
  }, [isThinking, thinkingStartTime])

  return (
    <div className="ink-conversation">
      <div className="ink-scroll" ref={scrollRef}>
        {displayMessages.map((msg, idx) => (
          <div
            key={msg.id}
            className={`ink-trace ${msg.role === 'user' ? 'ink-trace-user' : 'ink-trace-ai'}`}
          >
            <div className="ink-trace-header">
              <span className={`ink-trace-label ${msg.role === 'user' ? 'ink-trace-label-user' : 'ink-trace-label-ai'}`}>
                {msg.role === 'user' ? '问' : '枢'}
              </span>
              <span className="ink-trace-time">{formatTime(msg.timestamp)}</span>
              {msg.role === 'assistant' && idx > 0 && displayMessages[idx - 1]?.role === 'user' && (
                <span className="ink-trace-think-time">
                  思考 {formatDuration(msg.timestamp - displayMessages[idx - 1].timestamp)}
                </span>
              )}
            </div>
            {msg.role === 'assistant' ? (
              <div className="ink-trace-text ink-trace-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
                {msg.interactiveOptions && msg.interactiveOptions.length > 0 && onOptionClick && (
                  <InteractiveOptions options={msg.interactiveOptions} onOptionClick={onOptionClick} />
                )}
              </div>
            ) : (
              <div className="ink-trace-text">{msg.content}</div>
            )}
            <div className="ink-trace-divider" />
          </div>
        ))}
        {isThinking && (
          <div className="ink-trace ink-trace-ai ink-trace-thinking">
            <div className="ink-trace-header">
              <span className="ink-trace-label ink-trace-label-ai">枢</span>
              <span className="ink-trace-time">{thinkingStartTime ? formatTime(thinkingStartTime) : ''}</span>
              <span className="ink-trace-think-time ink-think-active">
                思考中 {thinkingDuration > 0 ? formatDuration(thinkingDuration) : ''}
              </span>
            </div>
            <div className="ink-trace-text ink-thinking-dots">
              <span className="ink-dot" />
              <span className="ink-dot" />
              <span className="ink-dot" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
