import React from 'react';

export default function RatingPanel() {
  return (
    <div className="w-full max-w-5xl mx-auto bg-slate-900/60 backdrop-blur-md border border-white/10 rounded p-6 flex items-center justify-between shadow-lg relative overflow-hidden">
      {/* Subtle bottom glow in the panel */}
      <div className="absolute -bottom-10 left-1/2 transform -translate-x-1/2 w-3/4 h-24 bg-cyan-500/20 blur-2xl z-0 pointer-events-none" />

      <div className="flex items-center gap-12 z-10 text-slate-200">
        <div className="flex flex-col font-mono text-[10px] uppercase mb-1">
          <span className="text-slate-500 tracking-widest">阶段完成</span>
          <span className="text-cyan-400 font-bold tracking-widest text-sm mt-1">AI 评分</span>
        </div>

        {/* Big '优' score character */}
        <div className="text-[5rem] font-serif text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,0.4)] mx-4 leading-none select-none">
          优
        </div>

        <div className="flex gap-10 pl-6 border-l border-white/10 font-mono">
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] text-slate-500 tracking-widest uppercase">理解深度</span>
            <span className="text-2xl font-bold text-white">95</span>
          </div>
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] text-slate-500 tracking-widest uppercase">信息质量</span>
            <span className="text-2xl font-bold text-white">92</span>
          </div>
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] text-slate-500 tracking-widest uppercase">表达清晰度</span>
            <span className="text-2xl font-bold text-white">90</span>
          </div>
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] text-slate-500 tracking-widest uppercase">问题解决度</span>
            <span className="text-2xl font-bold text-white">94</span>
          </div>
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] text-emerald-400 tracking-widest uppercase font-bold">综合评分</span>
            <span className="text-2xl font-bold text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.5)]">93</span>
          </div>
        </div>
      </div>

      <button className="z-10 group relative px-6 py-2 bg-transparent hover:bg-cyan-500/10 border border-cyan-500/50 rounded transition-all duration-300 flex items-center gap-4 overflow-hidden">
        <span className="text-cyan-400 tracking-widest font-mono text-[11px] uppercase font-bold relative z-10">继续对话</span>
        <span className="text-cyan-300 group-hover:translate-x-1.5 transition-transform duration-300 relative z-10 font-mono font-bold">→</span>
      </button>
    </div>
  );
}
