'use client'

import type { InkMessage, ProjectOrb } from '../../types/consciousness'
import { PHASE_COLORS } from '../../types/consciousness'

interface Props {
  messages: InkMessage[]
  artifacts: string[]
  orb: ProjectOrb | null
  allOrbs: ProjectOrb[]
  onClose: () => void
  onOrbSelect: (orbId: string) => void
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts)
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  const s = d.getSeconds().toString().padStart(2, '0')
  return `${h}:${m}:${s}`
}

function formatDate(ts: number): string {
  const d = new Date(ts)
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  return `${month}/${day}`
}

export default function HistoryPanel({ messages, artifacts, orb, allOrbs, onClose, onOrbSelect }: Props) {
  const phaseColor = orb ? (PHASE_COLORS[orb.phase] || PHASE_COLORS.qishu) : null

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel history-panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">
          <span className="slash">/</span>对话记录
        </div>

        {allOrbs.length > 1 && (
          <div className="history-orbs-section">
            <div className="history-section-label">项目</div>
            <div className="history-orbs-list">
              {allOrbs.map((o) => {
                const color = PHASE_COLORS[o.phase] || PHASE_COLORS.qishu
                const isActive = orb?.id === o.id
                return (
                  <div
                    key={o.id}
                    className={`history-orb-item ${isActive ? 'active' : ''}`}
                    onClick={() => onOrbSelect(o.id)}
                  >
                    <div
                      className="history-orb-dot"
                      style={{
                        background: `radial-gradient(circle at 35% 35%, rgba(${Math.min(255, color.r + 80)}, ${Math.min(255, color.g + 80)}, ${Math.min(255, color.b + 80)}, 0.6), rgba(${color.r}, ${color.g}, ${color.b}, 0.3))`,
                        boxShadow: isActive ? `0 0 12px rgba(${color.r}, ${color.g}, ${color.b}, 0.4)` : 'none',
                      }}
                    />
                    <div className="history-orb-info">
                      <div className="history-orb-phase">{o.phaseLabel}</div>
                      <div className="history-orb-date">{formatDate(o.createdAt)}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {orb && phaseColor && (
          <div className="history-phase-badge" style={{
            borderColor: `rgba(${phaseColor.r}, ${phaseColor.g}, ${phaseColor.b}, 0.4)`,
            color: `rgba(${phaseColor.r}, ${phaseColor.g}, ${phaseColor.b}, 0.9)`,
          }}>
            {orb.phaseLabel}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
          {messages.map((msg) => (
            <div key={msg.id} className="history-message">
              <div className="history-message-header">
                <span className={`history-message-role ${msg.role === 'user' ? 'role-user' : 'role-ai'}`}>
                  {msg.role === 'user' ? '问' : '枢'}
                </span>
                <span className="history-message-time">{formatTimestamp(msg.timestamp)}</span>
              </div>
              <div className="history-message-content">
                {msg.content}
              </div>
            </div>
          ))}
          {messages.length === 0 && (
            <div className="history-empty">尚无墨迹</div>
          )}
        </div>

        {artifacts.length > 0 && (
          <div className="history-artifacts-section">
            <div className="history-section-label">文件</div>
            <div className="history-artifacts-list">
              {artifacts.map((name, i) => (
                <div key={i} className="history-artifact-item">
                  <span className="artifact-icon">📄</span>
                  <span className="artifact-name">{name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
