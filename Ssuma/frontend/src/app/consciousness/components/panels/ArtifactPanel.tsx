'use client'

interface Artifact {
  phase: string
  summary: string
  decisions_count: number
  open_questions_count: number
}

interface Props {
  artifacts: Artifact[]
  onClose: () => void
}

export default function ArtifactPanel({ artifacts, onClose }: Props) {
  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">
          <span className="slash">/</span>产物
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {artifacts.map((artifact, i) => (
            <div key={i} style={{
              padding: '12px 0',
              borderBottom: '1px solid rgba(128,128,128,0.06)',
            }}>
              <div style={{
                fontSize: '11px',
                fontWeight: 700,
                opacity: 0.6,
                marginBottom: '6px',
                letterSpacing: '0.1em',
              }}>
                {artifact.phase}
              </div>
              <div style={{
                fontSize: '13px',
                lineHeight: '2.1',
                opacity: 0.65,
              }}>
                {artifact.summary}
              </div>
              <div style={{
                display: 'flex',
                gap: '16px',
                marginTop: '8px',
                fontSize: '9px',
                fontWeight: 200,
                opacity: 0.4,
              }}>
                <span>{artifact.decisions_count} 决策</span>
                <span>{artifact.open_questions_count} 待决</span>
              </div>
            </div>
          ))}
          {artifacts.length === 0 && (
            <div style={{
              fontSize: '11px',
              fontWeight: 200,
              opacity: 0.3,
              textAlign: 'center',
              padding: '32px 0',
            }}>
              尚无产物
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
