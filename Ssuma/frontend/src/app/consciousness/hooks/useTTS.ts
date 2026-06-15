'use client'

import { useState, useCallback, useRef, useEffect } from 'react'

const TTS_BASE_URL = ''

export interface TTSState {
  isPlaying: boolean
  currentText: string
  voice: string
  queue: string[]
}

export function useTTS(defaultVoice = 'robot') {
  const [state, setState] = useState<TTSState>({
    isPlaying: false,
    currentText: '',
    voice: defaultVoice,
    queue: [],
  })

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const queueRef = useRef<string[]>([])
  const isProcessingRef = useRef(false)
  const voiceRef = useRef(defaultVoice)

  const processQueue = useCallback(async () => {
    if (isProcessingRef.current) return
    isProcessingRef.current = true

    while (queueRef.current.length > 0) {
      const text = queueRef.current.shift()!
      const voice = voiceRef.current
      setState(prev => ({ ...prev, isPlaying: true, currentText: text, queue: [...queueRef.current] }))

      try {
        const url = `${TTS_BASE_URL}/api/v1/voice/tts?text=${encodeURIComponent(text)}&voice=${voice}`
        console.log('[TTS] Fetching:', url.substring(0, 100))
        const audio = new Audio(url)
        audioRef.current = audio

        // Wait for audio to be ready before playing
        await new Promise<void>((resolve, reject) => {
          audio.oncanplaythrough = () => {
            audio.play().then(resolve).catch(reject)
          }
          audio.onerror = () => reject(new Error('Audio load error'))
          // Timeout after 15s
          setTimeout(() => reject(new Error('TTS timeout')), 15000)
        })

        // Wait for playback to finish
        await new Promise<void>((resolve) => {
          if (audioRef.current !== audio) { resolve(); return }
          audio.onended = () => resolve()
          // Safety timeout
          setTimeout(resolve, 30000)
        })

        console.log('[TTS] Playback finished for:', text.substring(0, 30))
      } catch (e) {
        console.warn('[TTS] Error:', e)
      } finally {
        audioRef.current = null
      }
    }

    isProcessingRef.current = false
    setState(prev => ({ ...prev, isPlaying: false, currentText: '', queue: [] }))
  }, [])

  const speak = useCallback((text: string, voice?: string) => {
    if (voice) voiceRef.current = voice
    const v = voice || voiceRef.current

    // Strip markdown syntax for cleaner speech
    const cleanText = text
      .replace(/```[\s\S]*?```/g, '代码块')
      .replace(/`[^`]+`/g, '代码')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/#{1,6}\s/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[-*]\s/g, '')
      .replace(/\d+\.\s/g, '')
      .replace(/[①②③④⑤]/g, '')
      .trim()

    if (!cleanText) return

    // Split long text into sentences for better TTS
    const sentences = cleanText.match(/[^。！？.!?\n]+[。！？.!?\n]?/g) || [cleanText]
    const chunks: string[] = []
    let current = ''

    for (const s of sentences) {
      if ((current + s).length > 200) {
        if (current) chunks.push(current)
        current = s
      } else {
        current += s
      }
    }
    if (current) chunks.push(current)

    console.log('[TTS] Queuing', chunks.length, 'chunks, voice:', v)
    queueRef.current.push(...chunks)
    setState(prev => ({ ...prev, voice: v, queue: [...queueRef.current] }))
    processQueue()
  }, [processQueue])

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    queueRef.current = []
    isProcessingRef.current = false
    setState(prev => ({ ...prev, isPlaying: false, currentText: '', queue: [] }))
  }, [])

  const setVoice = useCallback((voice: string) => {
    voiceRef.current = voice
    setState(prev => ({ ...prev, voice }))
  }, [])

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      queueRef.current = []
      isProcessingRef.current = false
    }
  }, [])

  return {
    ttsState: state,
    speak,
    stop,
    setVoice,
  }
}
