'use client'

import { useFlowContext } from '../../context/FlowContext'

interface Props {
  loading: boolean
  progress: number
  isVoiceMode: boolean
}

export default function QuickActions({ loading, isVoiceMode }: Props) {
  const { state, handleExport } = useFlowContext()

  const { canExport, currentPhase } = state

  const showExport = canExport || currentPhase === 'ningmo'

  const onExport = async () => {
    await handleExport()
  }

  if (isVoiceMode) return null

  return (
    <div className="quick-actions">
      {showExport && (
        <button
          className="quick-action-btn export-btn"
          onClick={onExport}
          title="导出 AI IDE 项目文件（Cursor/Claude/Copilot）"
        >
          <span className="qa-icon">📦</span>
          <span className="qa-label">导出 IDE 文件</span>
        </button>
      )}

      <style jsx>{`
        .quick-actions {
          position: fixed;
          bottom: 120px;
          right: 24px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          z-index: 40;
        }
        .quick-action-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.06);
          color: rgba(255, 255, 255, 0.85);
          font-size: 12px;
          cursor: pointer;
          backdrop-filter: blur(12px);
          transition: all 0.2s;
          white-space: nowrap;
        }
        .quick-action-btn:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(255, 255, 255, 0.25);
        }
        .quick-action-btn:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .export-btn {
          border-color: rgba(212, 168, 67, 0.3);
        }
        .export-btn:hover:not(:disabled) {
          border-color: rgba(212, 168, 67, 0.6);
          background: rgba(212, 168, 67, 0.12);
        }
        .qa-icon {
          font-size: 14px;
        }
        .qa-label {
          font-weight: 500;
        }
      `}</style>
    </div>
  )
}
