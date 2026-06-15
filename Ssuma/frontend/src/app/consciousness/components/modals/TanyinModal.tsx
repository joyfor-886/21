'use client'

import type { Tanyin } from '../../types/consciousness'

interface Props {
  tanyin: Tanyin
  answers: Record<string, string[]>
  textAnswers: Record<string, string>
  onToggleOption: (itemIndex: number, option: string) => void
  onSetRadio: (itemIndex: number, option: string) => void
  onSetText: (itemIndex: number, value: string) => void
  onSubmit: () => void
  onClose: () => void
}

export default function TanyinModal({
  tanyin,
  answers,
  textAnswers,
  onToggleOption,
  onSetRadio,
  onSetText,
  onSubmit,
  onClose,
}: Props) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="tanyin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="tanyin-title">{tanyin.title}</div>
        <div className="tanyin-divider" />

        {tanyin.items.map((item, i) => (
          <div key={i} className="tanyin-item">
            <div className="tanyin-item-label">
              {item.label}
              {item.required && <span style={{ color: 'var(--seal-red)', marginLeft: '4px' }}>*</span>}
            </div>

            {item.type === 'checkbox' && item.options?.map((opt) => {
              const isChecked = (answers[i] || []).includes(opt)
              return (
                <div
                  key={opt}
                  className="tanyin-option"
                  onClick={() => onToggleOption(i, opt)}
                >
                  <div className={`q-checkbox ${isChecked ? 'checked' : ''}`}>
                    {isChecked && <span style={{ fontSize: '10px', color: 'var(--accent-gold)' }}>✓</span>}
                  </div>
                  <span>{opt}</span>
                </div>
              )
            })}

            {item.type === 'radio' && item.options?.map((opt) => {
              const isChecked = (answers[i] || []).includes(opt)
              return (
                <div
                  key={opt}
                  className="tanyin-option"
                  onClick={() => onSetRadio(i, opt)}
                >
                  <div className={`q-radio ${isChecked ? 'checked' : ''}`}>
                    <div className="q-radio-dot" />
                  </div>
                  <span>{opt}</span>
                </div>
              )
            })}

            {item.type === 'text' && (
              <input
                className="q-text-input"
                value={textAnswers[i] || ''}
                onChange={(e) => onSetText(i, e.target.value)}
                placeholder={item.placeholder || '请输入...'}
              />
            )}
          </div>
        ))}

        <button className="tanyin-confirm" onClick={onSubmit}>
          确 认
        </button>
      </div>
    </div>
  )
}
