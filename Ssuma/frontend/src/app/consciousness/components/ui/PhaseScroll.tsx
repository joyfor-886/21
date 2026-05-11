'use client'

import type { PhaseInfo } from '../../types/consciousness'

interface Props {
  phases: PhaseInfo[]
  onPhaseClick: (phaseKey: string) => void
  isVoiceMode: boolean
}

const PHASE_ORDER = ['qishu', 'questionnaire', 'caiheng', 'zhenwei', 'ceshu', 'ningmo']

export default function PhaseScroll({ phases, onPhaseClick, isVoiceMode }: Props) {
  const orderedPhases = PHASE_ORDER
    .map(key => phases.find(p => p.key === key))
    .filter(Boolean) as PhaseInfo[]

  return (
    <div className={`phase-scroll ${isVoiceMode ? 'hidden' : ''}`}>
      {orderedPhases.map((phase, i) => (
        <span key={phase.key}>
          <div
            className={`phase-mark ${phase.isCurrent ? 'current' : ''} ${phase.isComplete ? 'complete' : ''}`}
            onClick={() => onPhaseClick(phase.key)}
          >
            <div className="phase-dot" />
            <span className="phase-label">{phase.label}</span>
          </div>
          {i < orderedPhases.length - 1 && <div className="phase-vein" />}
        </span>
      ))}
    </div>
  )
}
