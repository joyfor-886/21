'use client'

import type { GradeLevel } from '../../types/consciousness'

interface Props {
  grade: GradeLevel | null
}

const GRADE_MAP: Record<GradeLevel, { char: string; className: string }> = {
  supreme: { char: '极', className: 'grade-supreme' },
  excellent: { char: '优', className: 'grade-excellent' },
  good: { char: '良', className: 'grade-good' },
  pass: { char: '可', className: 'grade-pass' },
}

export default function GradeOverlay({ grade }: Props) {
  if (!grade) return null

  const { char, className } = GRADE_MAP[grade]

  return (
    <div className="grade-overlay">
      <div className={`grade-character ${className}`}>
        {char}
      </div>
    </div>
  )
}
