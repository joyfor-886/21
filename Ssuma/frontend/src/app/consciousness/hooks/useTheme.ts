'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Theme } from '../types/consciousness'

export function useTheme(defaultTheme: Theme = 'xuanmo') {
  const [theme, setTheme] = useState<Theme>(defaultTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'xuanmo' ? 'xuanzhi' : 'xuanmo')
  }, [])

  return { theme, setTheme, toggleTheme }
}
