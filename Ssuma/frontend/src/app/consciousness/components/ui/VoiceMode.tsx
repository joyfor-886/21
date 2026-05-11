'use client'

import type { VoiceState } from '../../types/consciousness'

interface Props {
  voiceState: VoiceState
  onToggle: () => void
}

export default function VoiceMode({ voiceState, onToggle }: Props) {
  if (!voiceState.isListening) return null

  return (
    <div className="voice-mode">
      <div className="voice-icon-center" onClick={onToggle}>
        言
      </div>
      {voiceState.transcript && (
        <div className="voice-hint">{voiceState.transcript}</div>
      )}
    </div>
  )
}
