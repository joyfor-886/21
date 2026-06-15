'use client'

import { useState, useCallback } from 'react'
import type { Tanyin, TanyinItem } from '../types/consciousness'

export function useTanyin() {
  const [tanyin, setTanyin] = useState<Tanyin | null>(null)
  const [answers, setAnswers] = useState<Record<string, string[]>>({})
  const [textAnswers, setTextAnswers] = useState<Record<string, string>>({})

  const openTanyin = useCallback((q: Tanyin) => {
    setTanyin(q)
    const initialAnswers: Record<string, string[]> = {}
    const initialText: Record<string, string> = {}
    q.items.forEach((item, i) => {
      initialAnswers[i] = []
      initialText[i] = ''
    })
    setAnswers(initialAnswers)
    setTextAnswers(initialText)
  }, [])

  const closeTanyin = useCallback(() => {
    setTanyin(null)
    setAnswers({})
    setTextAnswers({})
  }, [])

  const toggleOption = useCallback((itemIndex: number, option: string) => {
    setAnswers(prev => {
      const current = prev[itemIndex] || []
      const idx = current.indexOf(option)
      if (idx >= 0) {
        return { ...prev, [itemIndex]: current.filter(o => o !== option) }
      }
      return { ...prev, [itemIndex]: [...current, option] }
    })
  }, [])

  const setRadioOption = useCallback((itemIndex: number, option: string) => {
    setAnswers(prev => ({ ...prev, [itemIndex]: [option] }))
  }, [])

  const setTextAnswer = useCallback((itemIndex: number, value: string) => {
    setTextAnswers(prev => ({ ...prev, [itemIndex]: value }))
  }, [])

  const submitAnswers = useCallback(() => {
    if (!tanyin) return null
    const result = tanyin.items.map((item, i) => ({
      label: item.label,
      type: item.type,
      value: item.type === 'text' ? textAnswers[i] || '' : answers[i] || [],
    }))
    closeTanyin()
    return result
  }, [tanyin, answers, textAnswers, closeTanyin])

  return {
    tanyin,
    answers,
    textAnswers,
    openTanyin,
    closeTanyin,
    toggleOption,
    setRadioOption,
    setTextAnswer,
    submitAnswers,
  }
}
