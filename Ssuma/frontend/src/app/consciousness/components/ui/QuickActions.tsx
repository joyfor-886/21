'use client'

interface Props {
  loading: boolean
  progress: number
  isVoiceMode: boolean
}

export default function QuickActions({ loading, progress, isVoiceMode }: Props) {
  return (
    <div className={`quick-actions ${isVoiceMode || loading ? 'hidden' : ''}`}>
      <button className="quick-action">/对话记录</button>
      <button className="quick-action">/产物</button>
    </div>
  )
}
