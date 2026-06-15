'use client'

import type { PanelType, TechMetrics } from '../../types/consciousness'
import { COMPLEXITY_LABELS } from '../../../../lib/constants'
import SsumaLogo from './SsumaLogo'

interface Props {
  onLinkClick: (type: PanelType) => void
  techMetrics: TechMetrics
  sessionTurns: number
  complexity: string
  complexityLabel: string
  isVoiceMode: boolean
}

export default function BrandPanel({ onLinkClick, techMetrics, sessionTurns, complexity, complexityLabel, isVoiceMode }: Props) {
  const complexityInfo = COMPLEXITY_LABELS[complexity]

  return (
    <div className={`brand-panel ${isVoiceMode ? 'hidden' : ''}`}>
      <SsumaLogo />

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
        <div
          className="brand-link"
          onClick={() => onLinkClick('mcp')}
        >
          <span className="slash">/</span>工具
        </div>
      </div>

      {complexityInfo && (
        <div className="brand-complexity">
          <span
            className="complexity-dot"
            style={{ background: complexityInfo.color }}
          />
          <span className="complexity-label">
            项目复杂度：{complexityLabel || complexityInfo.label}
          </span>
        </div>
      )}

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

      <style jsx>{`
        .brand-complexity {
          display: flex;
          align-items: center;
          gap: 6px;
          margin: 4px 0;
          padding: 3px 8px;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.04);
        }
        .complexity-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .complexity-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.5);
        }
      `}</style>
    </div>
  )
}
