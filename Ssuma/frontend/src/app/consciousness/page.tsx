'use client'

import dynamic from 'next/dynamic'
import { useTheme } from './hooks/useTheme'
import { useConsciousness } from './hooks/useConsciousness'
import { useFlowContext, FlowProvider } from './context/FlowContext'

import InkConversation from './components/ui/InkConversation'
import InputLine from './components/ui/InputLine'
import PhaseScroll from './components/ui/PhaseScroll'
import BrandPanel from './components/ui/BrandPanel'
import GradeOverlay from './components/ui/GradeOverlay'
import LoadingIndicator from './components/ui/LoadingIndicator'
import QuickActions from './components/ui/QuickActions'
import HistoryPanel from './components/panels/HistoryPanel'
import ArtifactPanel from './components/panels/ArtifactPanel'
import StudyPanel from './components/panels/StudyPanel'
import TanyinModal from './components/modals/TanyinModal'
import HITLCard from './components/HITLCard'
import MCPPanel from './components/MCPPanel'

const ConsciousnessScene = dynamic(
  () => import('./components/ConsciousnessScene').then(m => {
    const Comp = m.default
    return (props: React.ComponentProps<typeof Comp>) => <Comp {...props} />
  }),
  { ssr: false }
)

function ConsciousnessContent() {
  const { state, dispatch, handlePhaseClick, handlePanelClick, handleApplyConfig, handleOrbClick } = useFlowContext()
  const { phases, artifacts, llmConfig, activePanel, grade, techMetrics, sessionTurns, orbs, selectedOrbId, complexity, complexityLabel, currentPhase } = state

  const { theme, toggleTheme } = useTheme('xuanmo')
  const {
    messages, loading, loadingProgress, handleSend, handleOptionClick,
    voiceState, isVoiceMode, voiceVisualLabel,
    tanyin, answers, textAnswers, closeTanyin, toggleOption, setRadioOption, setTextAnswer, handleTanyinSubmit,
    thinkingStartTime, hitlInterrupt, clearHITL,
  } = useConsciousness()

  const selectedOrb = orbs.find(o => o.id === selectedOrbId) || null
  const artifactNames = artifacts.map((a) => a.phase || a.summary)

  return (
    <div className="consciousness-space">
      <ConsciousnessScene
        currentPhase={currentPhase}
        voiceAmplitude={voiceState.amplitude}
        voiceLowFreq={voiceState.lowFreq}
        voiceMidFreq={voiceState.midFreq}
        voiceHighFreq={voiceState.highFreq}
        theme={theme}
        isThinking={loading}
        orbs={orbs}
        onOrbClick={handleOrbClick}
      />

      <div className={`ui-overlay${activePanel ? ' panel-open' : ''}`}>
        <InkConversation messages={messages} isThinking={loading} thinkingStartTime={thinkingStartTime} onOptionClick={handleOptionClick} />

        <PhaseScroll
          phases={phases}
          onPhaseClick={handlePhaseClick}
          isVoiceMode={isVoiceMode}
        />

        <InputLine
          onSend={handleSend}
          disabled={loading}
        />

        {(voiceState.isListening || voiceState.isProcessing) && (
          <div className="voice-debug" style={{
            position: 'absolute',
            bottom: 'clamp(50px, 8vh, 90px)',
            left: '50%',
            transform: 'translateX(-50%)',
            fontSize: '12px',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-serif)',
            pointerEvents: 'none',
          }}>
            {voiceState.isProcessing ? '⏳' : '🎤'} {voiceState.isProcessing ? (voiceState.transcript || '正在识别...') : (voiceState.transcript || '正在聆听...')}
          </div>
        )}

        <div className="voice-mode-hint">{voiceVisualLabel} · V切换</div>

        <LoadingIndicator loading={loading} progress={loadingProgress} />

        <QuickActions
          loading={loading}
          progress={loadingProgress}
          isVoiceMode={isVoiceMode}
        />

        <BrandPanel
          onLinkClick={handlePanelClick}
          techMetrics={techMetrics}
          sessionTurns={sessionTurns}
          complexity={complexity}
          complexityLabel={complexityLabel}
          isVoiceMode={isVoiceMode}
        />

        <GradeOverlay grade={grade} />

        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'xuanmo' ? '墨' : '纸'}
        </button>

        {activePanel === 'history' && (
          <HistoryPanel
            messages={selectedOrb?.messages || messages}
            artifacts={selectedOrb?.artifacts || artifactNames}
            orb={selectedOrb}
            allOrbs={orbs}
            onClose={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
            onOrbSelect={(orbId) => dispatch({ type: 'SET_SELECTED_ORB_ID', payload: orbId })}
          />
        )}

        {activePanel === 'artifact' && (
          <ArtifactPanel
            artifacts={artifacts}
            onClose={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
          />
        )}

        {activePanel === 'study' && (
          <StudyPanel
            config={llmConfig}
            onClose={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
            onApply={handleApplyConfig}
          />
        )}

        {tanyin && (
          <TanyinModal
            tanyin={tanyin}
            answers={answers}
            textAnswers={textAnswers}
            onToggleOption={toggleOption}
            onSetRadio={setRadioOption}
            onSetText={setTextAnswer}
            onSubmit={handleTanyinSubmit}
            onClose={closeTanyin}
          />
        )}

        {hitlInterrupt && (
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 animate-[inkRiseAI_0.4s_ease_forwards]">
            <HITLCard
              interrupt={hitlInterrupt}
              projectId={state.projectId || ''}
              onRespond={clearHITL}
            />
          </div>
        )}

        {activePanel === 'mcp' && (
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-40">
            <MCPPanel />
            <button
              className="absolute -top-2 -right-2 w-6 h-6 flex items-center justify-center bg-ink/30 hover:bg-ink/50 text-ink-light text-xs rounded-full transition-colors"
              onClick={() => dispatch({ type: 'SET_ACTIVE_PANEL', payload: null })}
            >
              x
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ConsciousnessPage() {
  return (
    <FlowProvider>
      <ConsciousnessContent />
    </FlowProvider>
  )
}
