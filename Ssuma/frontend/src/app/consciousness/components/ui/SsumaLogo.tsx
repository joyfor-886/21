'use client'

import { useTheme } from '../../hooks/useTheme'

interface Props {
  className?: string
  style?: React.CSSProperties
}

export default function SsumaLogo({ className, style }: Props) {
  const { theme } = useTheme()
  const src = theme === 'xuanzhi' ? '/ssuma-logo-light.svg' : '/ssuma-logo.svg'

  return (
    <img
      src={src}
      alt="枢墨"
      className={`ssuma-logo ${className || ''}`}
      style={style}
      draggable={false}
    />
  )
}
