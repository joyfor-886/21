'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import type { VoiceState } from '../types/consciousness'

export function useVoiceMode() {
  const [voiceState, setVoiceState] = useState<VoiceState>({
    isListening: false,
    amplitude: 0,
    transcript: '',
  })
  const recognitionRef = useRef<any>(null)

  const startListening = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'zh-CN'

    recognition.onresult = (event: any) => {
      let transcript = ''
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
      }
      setVoiceState(prev => ({ ...prev, transcript }))
    }

    recognition.onerror = () => {
      setVoiceState(prev => ({ ...prev, isListening: false }))
    }

    recognition.onend = () => {
      setVoiceState(prev => ({ ...prev, isListening: false }))
    }

    recognitionRef.current = recognition
    recognition.start()
    setVoiceState(prev => ({ ...prev, isListening: true, transcript: '' }))
  }, [])

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
    setVoiceState(prev => ({ ...prev, isListening: false }))
  }, [])

  const toggleListening = useCallback(() => {
    if (voiceState.isListening) {
      stopListening()
    } else {
      startListening()
    }
  }, [voiceState.isListening, startListening, stopListening])

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
    }
  }, [])

  return { voiceState, toggleListening, startListening, stopListening }
}
