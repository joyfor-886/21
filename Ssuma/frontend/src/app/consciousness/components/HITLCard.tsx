'use client'

import { useState } from 'react'
import type { HITLInterrupt } from '../../../lib/types'
import { submitHITLFeedback } from '../../../lib/api'
import { PHASE_LABELS } from '../../../lib/constants'

interface Props {
  interrupt: HITLInterrupt
  projectId: string
  onRespond: () => void
}

export default function HITLCard({ interrupt, projectId, onRespond }: Props) {
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [showEdit, setShowEdit] = useState(false)
  const [editContent, setEditContent] = useState(interrupt.content)
  const [submitting, setSubmitting] = useState(false)

  const phaseLabel = PHASE_LABELS[interrupt.phase]?.label ?? interrupt.phase

  const handleSubmit = async (responseType: 'accept' | 'ignore' | 'response' | 'edit', content?: string) => {
    setSubmitting(true)
    try {
      await submitHITLFeedback(projectId, responseType, content)
      onRespond()
    } finally {
      setSubmitting(false)
    }
  }

  const handleAccept = () => handleSubmit('accept')
  const handleIgnore = () => handleSubmit('ignore')

  const handleFeedbackSubmit = () => {
    if (!feedbackText.trim()) return
    handleSubmit('response', feedbackText.trim())
  }

  const handleEditSubmit = () => {
    if (!editContent.trim()) return
    handleSubmit('edit', editContent.trim())
  }

  return (
    <div className="bg-black/60 backdrop-blur-md border border-ink/20 rounded-sm p-5 max-w-md w-full font-[var(--font-serif)]">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-ink-light text-[10px] font-light tracking-[0.3em] uppercase">
          人机协同中断
        </span>
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--seal-red)] animate-pulse" />
      </div>

      {/* Phase & Reason */}
      <div className="mb-3">
        <div className="text-ink-light text-xs font-semibold tracking-wider mb-1">
          {phaseLabel}
        </div>
        <div className="text-ink/80 text-[13px] leading-relaxed">
          {interrupt.reason}
        </div>
      </div>

      {/* Content Summary */}
      <div className="bg-ink/5 border border-ink/10 rounded-sm p-3 mb-4">
        <div className="text-ink/50 text-[9px] font-light tracking-[0.2em] mb-1">
          内容摘要
        </div>
        {showEdit ? (
          <textarea
            className="w-full bg-transparent border border-ink/20 rounded-sm p-2 text-ink/80 text-[13px] leading-relaxed outline-none resize-none focus:border-ink/40 font-[var(--font-serif)]"
            rows={4}
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
          />
        ) : (
          <div className="text-ink/70 text-[13px] leading-[2] line-clamp-4">
            {interrupt.content}
          </div>
        )}
      </div>

      {/* Feedback Textarea */}
      {showFeedback && (
        <div className="mb-4 animate-[inkRiseAI_0.4s_ease_forwards]">
          <textarea
            className="w-full bg-ink/5 border border-ink/15 rounded-sm p-3 text-ink/80 text-[13px] leading-relaxed outline-none resize-none focus:border-ink/30 placeholder:text-ink/30 font-[var(--font-serif)]"
            rows={3}
            placeholder="输入反馈内容..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            autoFocus
          />
          <div className="flex justify-end mt-2">
            <button
              className="bg-ink/20 hover:bg-ink/30 text-ink-light text-[11px] px-3 py-1.5 rounded-sm transition-colors disabled:opacity-40"
              onClick={handleFeedbackSubmit}
              disabled={!feedbackText.trim() || submitting}
            >
              提交反馈
            </button>
          </div>
        </div>
      )}

      {/* Edit Submit */}
      {showEdit && (
        <div className="flex justify-end mb-4">
          <button
            className="bg-ink/20 hover:bg-ink/30 text-ink-light text-[11px] px-3 py-1.5 rounded-sm transition-colors disabled:opacity-40"
            onClick={handleEditSubmit}
            disabled={!editContent.trim() || submitting}
          >
            确认修改
          </button>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          className="bg-ink/20 hover:bg-ink/30 text-ink-light text-[11px] px-3 py-1.5 rounded-sm transition-colors disabled:opacity-40 tracking-wider"
          onClick={handleAccept}
          disabled={submitting}
        >
          确认继续
        </button>
        <button
          className="bg-ink/20 hover:bg-ink/30 text-ink-light text-[11px] px-3 py-1.5 rounded-sm transition-colors disabled:opacity-40 tracking-wider"
          onClick={handleIgnore}
          disabled={submitting}
        >
          跳过
        </button>
        <button
          className="bg-ink/20 hover:bg-ink/30 text-ink-light text-[11px] px-3 py-1.5 rounded-sm transition-colors disabled:opacity-40 tracking-wider"
          onClick={() => {
            setShowFeedback(!showFeedback)
            setShowEdit(false)
          }}
        >
          反馈
        </button>
        <button
          className="bg-ink/20 hover:bg-ink/30 text-ink-light text-[11px] px-3 py-1.5 rounded-sm transition-colors disabled:opacity-40 tracking-wider"
          onClick={() => {
            setShowEdit(!showEdit)
            setShowFeedback(false)
          }}
        >
          修改
        </button>
      </div>

      {/* Options hint */}
      {interrupt.options.length > 0 && (
        <div className="mt-3 pt-3 border-t border-ink/10">
          <div className="text-ink/40 text-[9px] tracking-[0.15em] mb-1">可选操作</div>
          <div className="flex flex-wrap gap-1.5">
            {interrupt.options.map((opt) => (
              <span
                key={opt}
                className="text-ink/50 text-[10px] bg-ink/8 px-2 py-0.5 rounded-sm"
              >
                {opt}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
