'use client'

import type { PanelType, TechMetrics } from '../../types/consciousness'

interface Props {
  onLinkClick: (type: PanelType) => void
  techMetrics: TechMetrics
  sessionTurns: number
  isVoiceMode: boolean
}

export default function BrandPanel({ onLinkClick, techMetrics, sessionTurns, isVoiceMode }: Props) {
  return (
    <div className={`brand-panel ${isVoiceMode ? 'hidden' : ''}`}>
      <div className="brand-header">
        <div className="brand-name-cn">枢墨</div>
        <div className="brand-name-en">SSUMA</div>
      </div>

      <div className="brand-seal">枢</div>

      <div className="brand-links">
        <div
          className="brand-link"
          onClick={() => onLinkClick('history')}
        >
          <span className="slash">/</span>对话记录
        </div>
        <div
          className="brand-link"
          onClick={() => onLinkClick('artifact')}
        >
          <span className="slash">/</span>产物
        </div>
        <div
          className="brand-link"
          onClick={() => onLinkClick('study')}
        >
          <span className="slash">/</span>文房
        </div>
      </div>

      <div className="brand-session">
        {sessionTurns} 轮
      </div>

      <div className="tech-metrics">
        <div className="tech-progress">
          <div className="tech-progress-bg" />
          <div
            className="tech-progress-fill"
            style={{ width: `${techMetrics.progress}%` }}
          />
          <div className="tech-progress-label">
            {Math.round(techMetrics.progress)}%
          </div>
        </div>
        <div className="tech-metric">
          {techMetrics.tokenCount} tokens
        </div>
        <div className="tech-metric">
          {techMetrics.latency}ms
        </div>
      </div>
    </div>
  )
}
