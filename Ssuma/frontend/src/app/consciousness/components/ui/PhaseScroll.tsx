'use client'

import type { PhaseInfo } from '../../types/consciousness'

interface Props {
  phases: PhaseInfo[]
  onPhaseClick: (phaseKey: string) => void
  isVoiceMode: boolean
}

const PHASE_ORDER = ['qishu', 'tanyin', 'caiheng', 'zhenwei', 'ceshu', 'ningmo']

export default function PhaseScroll({ phases, onPhaseClick, isVoiceMode }: Props) {
  const orderedPhases = PHASE_ORDER
    .map(key => phases.find(p => p.key === key))
    .filter(Boolean) as PhaseInfo[]

  return (
    <div className={`phase-scroll ${isVoiceMode ? 'hidden' : ''}`}>
    </div>
  )
}
