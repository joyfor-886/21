'use client'

import type { VoiceState } from '../../types/consciousness'
import type { TTSState } from '../../hooks/useTTS'

interface Props {
  voiceState: VoiceState
  ttsState: TTSState
  onStopTTS: () => void
}

export default function VoiceMode({ voiceState, ttsState, onStopTTS }: Props) {
  if (!voiceState.isListening && !voiceState.isProcessing && !ttsState.isPlaying) return null

  return (
    <div className="voice-mode">
      {(voiceState.isListening || voiceState.isProcessing) && (
        <div className="voice-listening">
          <div className="voice-icon-center">{voiceState.isProcessing ? '识' : '言'}</div>
          <div className="voice-amplitude-bar">
            <div
              className="voice-amplitude-fill"
              style={{ width: `${Math.min(voiceState.amplitude * 100 * 3, 100)}%` }}
            />
          </div>
          {voiceState.transcript && (
            <div className="voice-hint">{voiceState.transcript}</div>
          )}
          <div className="voice-mode-label">{voiceState.isProcessing ? '正在识别...' : '松开空格发送'}</div>
        </div>
      )}
      {ttsState.isPlaying && !voiceState.isListening && (
        <div className="voice-playing" onClick={onStopTTS}>
          <div className="voice-icon-center voice-icon-playing">播</div>
          <div className="voice-playing-waves">
            <span className="voice-wave-bar" />
            <span className="voice-wave-bar" />
            <span className="voice-wave-bar" />
            <span className="voice-wave-bar" />
            <span className="voice-wave-bar" />
          </div>
          <div className="voice-mode-label">点击停止播报</div>
        </div>
      )}
    </div>
  )
}
