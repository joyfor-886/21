import React, { useState } from 'react';
import ParticleWave, { WaveConfig, defaultWaveConfig } from './components/ParticleWave';

export default function App() {
  const [config, setConfig] = useState<WaveConfig>(defaultWaveConfig);
  const [showConfig, setShowConfig] = useState(true);

  const handleConfigChange = (key: keyof WaveConfig, value: number) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const renderSlider = (label: string, key: keyof WaveConfig, min: number, max: number, step: number = 0.001) => (
    <div className="flex flex-col gap-1 mb-2">
      <div className="flex justify-between text-xs text-slate-300">
        <span>{label}</span>
        <span>{config[key].toFixed(step < 0.1 ? 3 : 1)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={config[key]}
        onChange={e => handleConfigChange(key, parseFloat(e.target.value))}
        className="w-full h-1 bg-slate-700 rounded outline-none appearance-none cursor-pointer"
      />
    </div>
  );

  return (
    <div className="w-screen h-screen bg-slate-950 overflow-hidden relative select-none font-sans">
      <div className="absolute inset-0 z-0 bg-black">
        <ParticleWave config={config} />
        <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-black via-black/80 to-transparent pointer-events-none" />
      </div>

      {/* Control Panel Toggle */}
      <button 
        onClick={() => setShowConfig(!showConfig)}
        className="absolute top-4 right-4 z-50 bg-slate-800/80 hover:bg-slate-700 text-white px-3 py-1.5 rounded-md text-sm border border-slate-600 backdrop-blur"
      >
        {showConfig ? 'Hide Controls' : 'Show Controls'}
      </button>

      {/* Control Panel */}
      {showConfig && (
        <div className="absolute top-16 right-4 z-40 w-80 max-h-[calc(100vh-6rem)] overflow-y-auto bg-slate-900/80 backdrop-blur-md border border-slate-700 rounded-lg p-4 shadow-2xl text-white scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent">
          <h2 className="text-lg font-semibold mb-4 border-b border-slate-700 pb-2">Wave Config</h2>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-cyan-400 mb-2">1. Main Swell (主涌浪)</h3>
              {renderSlider('Amplitude', 'w1Amp', 0, 100, 1)}
              {renderSlider('Speed', 'w1Speed', 0, 5, 0.1)}
              {renderSlider('Frequency', 'w1Freq', 0.001, 0.05, 0.001)}
              {renderSlider('Dir X', 'w1DirX', -2, 2, 0.1)}
              {renderSlider('Dir Z', 'w1DirZ', -2, 2, 0.1)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-cyan-400 mb-2">2. Secondary Swell (副涌浪)</h3>
              {renderSlider('Amplitude', 'w2Amp', 0, 100, 1)}
              {renderSlider('Speed', 'w2Speed', 0, 5, 0.1)}
              {renderSlider('Frequency', 'w2Freq', 0.001, 0.05, 0.001)}
              {renderSlider('Dir X', 'w2DirX', -2, 2, 0.1)}
              {renderSlider('Dir Z', 'w2DirZ', -2, 2, 0.1)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-cyan-400 mb-2">3. Primary Ripples (主涟漪)</h3>
              {renderSlider('Amplitude', 'w3Amp', 0, 50, 1)}
              {renderSlider('Speed', 'w3Speed', 0, 5, 0.1)}
              {renderSlider('Frequency', 'w3Freq', 0.001, 0.1, 0.001)}
              {renderSlider('Dir X', 'w3DirX', -2, 2, 0.1)}
              {renderSlider('Dir Z', 'w3DirZ', -2, 2, 0.1)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-cyan-400 mb-2">4. Secondary Ripples (次波纹)</h3>
              {renderSlider('Amplitude', 'w4Amp', 0, 30, 1)}
              {renderSlider('Speed', 'w4Speed', 0, 5, 0.1)}
              {renderSlider('Frequency', 'w4Freq', 0.001, 0.1, 0.001)}
              {renderSlider('Dir X', 'w4DirX', -2, 2, 0.1)}
              {renderSlider('Dir Z', 'w4DirZ', -2, 2, 0.1)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-cyan-400 mb-2">5. Global Breathing (全局呼吸)</h3>
              {renderSlider('Amplitude', 'w5Amp', 0, 50, 1)}
              {renderSlider('Speed', 'w5Speed', 0, 2, 0.01)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-purple-400 mb-2">Camera Settings (相机设置)</h3>
              {renderSlider('Pitch (Degrees)', 'cameraPitch', 0, 90, 1)}
              {renderSlider('Y Offset', 'cameraY', -500, 500, 10)}
              {renderSlider('Height Base', 'cameraHeightBase', 0, 800, 10)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
