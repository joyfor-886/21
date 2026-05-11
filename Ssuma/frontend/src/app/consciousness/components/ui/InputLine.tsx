'use client'

import { useState, useRef, useCallback } from 'react'

interface Props {
  onSend: (content: string) => void
  onVoiceToggle: () => void
  isVoiceMode: boolean
  disabled?: boolean
}

export default function InputLine({ onSend, onVoiceToggle, isVoiceMode, disabled }: Props) {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (text.trim()) {
        onSend(text.trim())
        setText('')
      }
    }
  }, [text, onSend])

  return (
    <div className={`input-line ${isVoiceMode ? 'hidden' : ''}`}>
      <span className="pen-label">笔</span>
      <div className="input-line-bar">
        <input
          ref={inputRef}
          type="text"
          className="input-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="落墨处..."
          disabled={disabled}
        />
      </div>
      <button className="voice-btn" onClick={onVoiceToggle} title="语音模式">
        言
      </button>
    </div>
  )
}
