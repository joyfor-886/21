'use client'

import { useState, useCallback } from 'react'

interface Props {
  onSend: (content: string) => void
  disabled?: boolean
}

export default function InputLine({ onSend, disabled }: Props) {
  const [text, setText] = useState('')

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
    <div className="input-line">
      <div className="input-line-bar">
        <input
          type="text"
          className="input-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="落墨处... 按住空格语音"
          disabled={disabled}
        />
      </div>
    </div>
  )
}
