'use client'

import { useState, useEffect } from 'react'
import { fetchProviders, fetchModels } from '../../../../lib/api'
import type { FetchedModel, LLMConfig, ApplyModelConfigRequest } from '../../../../lib/types'

interface ProviderItem {
  name: string
  model: string
  base_url?: string
  type?: string
}

interface Props {
  config: LLMConfig | null
  onClose: () => void
  onApply: (config: ApplyModelConfigRequest) => void
}

export default function StudyPanel({ config, onClose, onApply }: Props) {
  const [mode, setMode] = useState(config?.mode || 'auto')
  const [provider, setProvider] = useState(config?.chat_model?.provider || '')
  const [model, setModel] = useState(config?.chat_model?.model || '')
  const [baseUrl, setBaseUrl] = useState(config?.chat_model?.base_url || '')
  const [apiKey, setApiKey] = useState(config?.chat_model?.api_key || '')
  const [providers, setProviders] = useState<ProviderItem[]>([])
  const [detectedModels, setDetectedModels] = useState<FetchedModel[]>([])
  const [fetchingModels, setFetchingModels] = useState(false)

  useEffect(() => {
    fetchProviders().then(setProviders)
  }, [])

  const handleProviderChange = async (name: string) => {
    setProvider(name)
    const found = providers.find(p => p.name === name)
    if (found) {
      setBaseUrl(found.base_url || '')
      setDetectedModels([])
      setFetchingModels(true)

      const providerType = found.type || inferProviderType(name)

      if (found.base_url && providerType) {
        const result = await fetchModels(providerType, found.base_url, apiKey || undefined)
        console.log('[StudyPanel] fetchModels result:', result)
        if (result.success && result.models) {
          setDetectedModels(result.models)
          if (result.models.length > 0) {
            setModel(result.models[0].name)
          }
        } else {
          console.warn('[StudyPanel] 模型检测失败:', result.error)
        }
      }
      setFetchingModels(false)
    }
  }

  function inferProviderType(name: string): string {
    const map: Record<string, string> = {
      ollama: 'ollama',
      lm_studio: 'lm_studio',
      lmstudio: 'lm_studio',
      openai: 'openai',
      claude: 'anthropic',
      anthropic: 'anthropic',
    }
    return map[name] || 'openai_compatible'
  }

  const handleApply = () => {
    onApply({
      mode,
      chat_provider: provider,
      chat_model: model,
      base_url: baseUrl || undefined,
      api_key: apiKey || undefined,
    })
  }

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">
          <span className="slash">/</span>文房
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <div style={{
              fontSize: '9px',
              fontWeight: 200,
              opacity: 0.4,
              marginBottom: '8px',
              letterSpacing: '0.2em',
            }}>
              模式
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              {['auto', 'manual'].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  style={{
                    fontSize: '11px',
                    fontWeight: mode === m ? 400 : 200,
                    opacity: mode === m ? 0.8 : 0.4,
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-serif)',
                    borderBottom: mode === m ? '1px solid var(--accent-gold)' : '1px solid transparent',
                    padding: '4px 0',
                    transition: 'all 0.4s ease',
                  }}
                >
                  {m === 'auto' ? '自动' : '手动'}
                </button>
              ))}
            </div>
          </div>

          {mode === 'manual' && (
            <>
              <div>
                <div style={{
                  fontSize: '9px',
                  fontWeight: 200,
                  opacity: 0.4,
                  marginBottom: '8px',
                  letterSpacing: '0.2em',
                }}>
                  供应商
                </div>
                {providers.length > 0 ? (
                  <select
                    value={provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'var(--ink-wash)',
                      border: '1px solid var(--text-muted)',
                      color: 'var(--text-primary)',
                      fontSize: '12px',
                      padding: '6px 10px',
                      fontFamily: 'var(--font-serif)',
                      outline: 'none',
                      cursor: 'pointer',
                      opacity: 0.7,
                    }}
                  >
                    <option value="" disabled>选择供应商...</option>
                    {providers.map((p) => (
                      <option key={p.name} value={p.name}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    className="q-text-input"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    placeholder="加载中..."
                    readOnly
                  />
                )}
              </div>

              <div>
                <div style={{
                  fontSize: '9px',
                  fontWeight: 200,
                  opacity: 0.4,
                  marginBottom: '8px',
                  letterSpacing: '0.2em',
                }}>
                  Model
                </div>
                {detectedModels.length > 0 ? (
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'var(--ink-wash)',
                      border: '1px solid var(--text-muted)',
                      color: 'var(--text-primary)',
                      fontSize: '12px',
                      padding: '6px 10px',
                      fontFamily: 'var(--font-serif)',
                      outline: 'none',
                      cursor: 'pointer',
                      opacity: 0.7,
                    }}
                  >
                    {detectedModels.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name}
                        {m.parameter_size ? ` (${m.parameter_size})` : ''}
                      </option>
                    ))}
                  </select>
                ) : fetchingModels ? (
                  <input
                    className="q-text-input"
                    value="检测模型中..."
                    readOnly
                  />
                ) : (
                  <input
                    className="q-text-input"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="选择供应商后自动检测"
                  />
                )}
              </div>

              <div>
                <div style={{
                  fontSize: '9px',
                  fontWeight: 200,
                  opacity: 0.4,
                  marginBottom: '8px',
                  letterSpacing: '0.2em',
                }}>
                  Base URL
                </div>
                <input
                  className="q-text-input"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://..."
                />
              </div>

              <div>
                <div style={{
                  fontSize: '9px',
                  fontWeight: 200,
                  opacity: 0.4,
                  marginBottom: '8px',
                  letterSpacing: '0.2em',
                }}>
                  API Key
                </div>
                <input
                  className="q-text-input"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                />
              </div>
            </>
          )}

          {config?.current_tier_label && (
            <div style={{
              fontSize: '9px',
              fontWeight: 200,
              opacity: 0.4,
              textAlign: 'center',
            }}>
              当前层级：{config.current_tier_label}
            </div>
          )}

          <button
            onClick={handleApply}
            style={{
              display: 'block',
              margin: '8px auto 0',
              fontSize: '11px',
              fontWeight: 200,
              color: 'var(--accent-gold)',
              opacity: 0.6,
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'var(--font-serif)',
              letterSpacing: '0.5em',
            }}
          >
            应用
          </button>
        </div>
      </div>
    </div>
  )
}