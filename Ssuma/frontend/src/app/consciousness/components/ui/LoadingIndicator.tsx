'use client'

interface Props {
  loading: boolean
  progress: number
}

export default function LoadingIndicator({ loading, progress }: Props) {
  if (!loading) return null

  return (
    <div className="loading-indicator">
      <span className="loading-text">墨行</span>
      <div className="loading-progress">
        <div
          className="loading-progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <span className="loading-pct">{Math.round(progress)}%</span>
    </div>
  )
}
