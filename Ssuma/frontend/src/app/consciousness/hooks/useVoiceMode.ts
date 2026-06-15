'use client'

import { useState, useCallback, useEffect, useRef } from 'react'

const STT_API_URL = '/api/v1/voice/stt'

// 浏览器原生 SpeechRecognition 类型声明
interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList
}
interface SpeechRecognitionResultList {
  length: number
  [index: number]: SpeechRecognitionResult
}
interface SpeechRecognitionResult {
  isFinal: boolean
  [index: number]: SpeechRecognitionAlternative
}
interface SpeechRecognitionAlternative {
  transcript: string
  confidence: number
}
interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
}

function getSpeechRecognition(): SpeechRecognitionInstance | null {
  const SR = (window as unknown as Record<string, unknown>).SpeechRecognition
    || (window as unknown as Record<string, unknown>).webkitSpeechRecognition
  if (!SR) return null
  return new (SR as new () => SpeechRecognitionInstance)()
}

export interface VoiceState {
  isListening: boolean
  isProcessing: boolean
  amplitude: number
  lowFreq: number
  midFreq: number
  highFreq: number
  transcript: string
  isSupported: boolean
}

export function useVoiceMode(onTranscript?: (text: string) => void) {
  const [voiceState, setVoiceState] = useState<VoiceState>({
    isListening: false,
    isProcessing: false,
    amplitude: 0,
    lowFreq: 0,
    midFreq: 0,
    highFreq: 0,
    transcript: '',
    isSupported: false,
  })

  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const amplitudeRafRef = useRef<number>(0)
  const onTranscriptRef = useRef(onTranscript)
  onTranscriptRef.current = onTranscript

  const isListeningRef = useRef(false)
  const speechRecRef = useRef<SpeechRecognitionInstance | null>(null)
  // 记住原生 SR 是否可用（国内网络下 Google SR 不可用，首次失败后直接跳过）
  const nativeSRBrokenRef = useRef(false)

  useEffect(() => {
    // 支持浏览器原生 SpeechRecognition 或 MediaRecorder
    const nativeSR = !!getSpeechRecognition()
    const mediaSupported = !!navigator.mediaDevices?.getUserMedia && !!window.MediaRecorder
    const supported = nativeSR || mediaSupported
    setVoiceState(prev => ({ ...prev, isSupported: supported }))
  }, [])

  const startAmplitude = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef.current = stream
      const ctx = new AudioContext()
      audioContextRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const update = () => {
        if (!analyserRef.current) return
        analyserRef.current.getByteFrequencyData(dataArray)
        const len = dataArray.length
        const third = Math.floor(len / 3)
        let low = 0, mid = 0, high = 0
        for (let i = 0; i < third; i++) low += dataArray[i]
        for (let i = third; i < third * 2; i++) mid += dataArray[i]
        for (let i = third * 2; i < len; i++) high += dataArray[i]
        low = low / third / 255
        mid = mid / third / 255
        high = high / (len - third * 2) / 255
        const avg = (low + mid + high) / 3
        setVoiceState(prev => ({ ...prev, amplitude: avg, lowFreq: low, midFreq: mid, highFreq: high }))
        amplitudeRafRef.current = requestAnimationFrame(update)
      }
      update()
    } catch (e) {
      console.warn('[Voice] Microphone access denied:', e)
    }
  }, [])

  const stopAmplitude = useCallback(() => {
    cancelAnimationFrame(amplitudeRafRef.current)
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop())
      mediaStreamRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    analyserRef.current = null
    setVoiceState(prev => ({ ...prev, amplitude: 0, lowFreq: 0, midFreq: 0, highFreq: 0 }))
  }, [])

  // Start listening (space pressed)
  // 优先使用浏览器原生 SpeechRecognition（免费、无需 API Key）
  // 回退到 MediaRecorder + 后端 STT
  const startListening = useCallback(async () => {
    if (isListeningRef.current) return

    const nativeSR = !nativeSRBrokenRef.current ? getSpeechRecognition() : null

    if (nativeSR) {
      // === 浏览器原生 SpeechRecognition ===
      nativeSR.continuous = true
      nativeSR.interimResults = true
      nativeSR.lang = 'zh-CN'
      speechRecRef.current = nativeSR

      let finalTranscript = ''

      nativeSR.onresult = (event: SpeechRecognitionEvent) => {
        let interim = ''
        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i]
          if (result.isFinal) {
            finalTranscript += result[0].transcript
          } else {
            interim += result[0].transcript
          }
        }
        const display = finalTranscript + interim
        setVoiceState(prev => ({ ...prev, transcript: display }))
      }

      nativeSR.onerror = async (event) => {
        console.warn('[Voice] Native SR error:', event.error)
        speechRecRef.current = null
        stopAmplitude()

        // no-speech / aborted 是正常结束，不需要回退
        if (event.error === 'no-speech' || event.error === 'aborted') {
          isListeningRef.current = false
          setVoiceState(prev => ({ ...prev, isListening: false }))
          return
        }

        // 网络错误等致命错误：标记原生 SR 不可用，自动回退到 MediaRecorder + 后端 STT
        nativeSRBrokenRef.current = true
        console.log('[Voice] Native SR failed, auto-falling back to MediaRecorder')
        isListeningRef.current = false
        setVoiceState(prev => ({ ...prev, isListening: false, transcript: '' }))

        // 自动启动 MediaRecorder 作为回退
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          mediaStreamRef.current = stream

          const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
              ? 'audio/webm'
              : 'audio/mp4'

          const recorder = new MediaRecorder(stream, { mimeType })
          chunksRef.current = []

          recorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
              chunksRef.current.push(e.data)
            }
          }

          recorder.onerror = () => {
            isListeningRef.current = false
            setVoiceState(prev => ({ ...prev, isListening: false }))
            stopAmplitude()
          }

          mediaRecorderRef.current = recorder
          recorder.start(250)
          isListeningRef.current = true
          startAmplitude()
          setVoiceState(prev => ({ ...prev, isListening: true, transcript: '', isProcessing: false }))
          console.log('[Voice] MediaRecorder fallback started, mimeType:', mimeType)
        } catch (e) {
          console.warn('[Voice] MediaRecorder fallback also failed:', e)
          isListeningRef.current = false
          setVoiceState(prev => ({ ...prev, isListening: false }))
        }
      }

      nativeSR.onend = () => {
        // 识别结束，提交最终结果
        isListeningRef.current = false
        setVoiceState(prev => ({ ...prev, isListening: false, isProcessing: false }))
        stopAmplitude()
        if (finalTranscript.trim() && onTranscriptRef.current) {
          onTranscriptRef.current(finalTranscript.trim())
        }
      }

      try {
        nativeSR.start()
        isListeningRef.current = true
        startAmplitude()
        setVoiceState(prev => ({ ...prev, isListening: true, transcript: '', isProcessing: false }))
        console.log('[Voice] Native SpeechRecognition started')
      } catch (e) {
        console.warn('[Voice] Native SR start failed, falling back to MediaRecorder:', e)
        speechRecRef.current = null
        // Fall through to MediaRecorder path below
      }
    }

    // 如果原生 SR 不可用或启动失败，使用 MediaRecorder
    if (!speechRecRef.current) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaStreamRef.current = stream

        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : 'audio/mp4'

        const recorder = new MediaRecorder(stream, { mimeType })
        chunksRef.current = []

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data)
          }
        }

        recorder.onerror = () => {
          isListeningRef.current = false
          setVoiceState(prev => ({ ...prev, isListening: false }))
          stopAmplitude()
        }

        mediaRecorderRef.current = recorder
        recorder.start(250)
        isListeningRef.current = true
        startAmplitude()
        setVoiceState(prev => ({ ...prev, isListening: true, transcript: '', isProcessing: false }))
        console.log('[Voice] MediaRecorder started, mimeType:', mimeType)
      } catch (e) {
        console.warn('[Voice] Failed to start recording:', e)
      }
    }
  }, [startAmplitude, stopAmplitude])

  // Stop listening (space released)
  const stopListening = useCallback(() => {
    if (!isListeningRef.current) return

    // 优先停止浏览器原生 SpeechRecognition
    const nativeSR = speechRecRef.current
    if (nativeSR) {
      try {
        nativeSR.stop()
      } catch {
        // ignore
      }
      speechRecRef.current = null
      // onend 回调会处理状态更新和提交结果
      return
    }

    // 回退：停止 MediaRecorder 并发送到后端 STT
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state === 'inactive') {
      isListeningRef.current = false
      setVoiceState(prev => ({ ...prev, isListening: false }))
      stopAmplitude()
      return
    }

    recorder.onstop = async () => {
      stopAmplitude()
      isListeningRef.current = false
      setVoiceState(prev => ({ ...prev, isListening: false }))

      const chunks = chunksRef.current
      if (chunks.length === 0) {
        setVoiceState(prev => ({ ...prev, isProcessing: false }))
        return
      }

      const mimeType = recorder.mimeType
      const blob = new Blob(chunks, { type: mimeType })

      if (blob.size < 2000) {
        setVoiceState(prev => ({ ...prev, isProcessing: false }))
        return
      }

      setVoiceState(prev => ({ ...prev, isProcessing: true, transcript: '正在识别...' }))

      try {
        const formData = new FormData()
        formData.append('audio', blob, `recording.${mimeType.includes('webm') ? 'webm' : 'mp4'}`)

        const response = await fetch(STT_API_URL, {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const errText = await response.text()
          console.error('[Voice] STT API error:', response.status, errText)
          setVoiceState(prev => ({ ...prev, isProcessing: false, transcript: '' }))
          return
        }

        const result = await response.json()
        const text = (result.text || '').trim()

        if (text && onTranscriptRef.current) {
          setVoiceState(prev => ({ ...prev, transcript: text, isProcessing: false }))
          onTranscriptRef.current(text)
        } else {
          setVoiceState(prev => ({ ...prev, transcript: '', isProcessing: false }))
        }
      } catch (e) {
        console.error('[Voice] STT request failed:', e)
        setVoiceState(prev => ({ ...prev, isProcessing: false, transcript: '' }))
      }
    }

    recorder.stop()
  }, [stopAmplitude])

  useEffect(() => {
    return () => {
      if (speechRecRef.current) {
        try { speechRecRef.current.abort() } catch { /* ignore */ }
        speechRecRef.current = null
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      stopAmplitude()
    }
  }, [stopAmplitude])

  return {
    voiceState,
    startListening,
    stopListening,
  }
}
