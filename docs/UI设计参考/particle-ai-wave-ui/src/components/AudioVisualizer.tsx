import React from 'react';
import { motion } from 'motion/react';
import { Mic } from 'lucide-react';

export default function AudioVisualizer() {
  const leftBars = Array.from({ length: 35 }).map((_, i) => ({
    id: i,
    height: Math.random() * 35 + 10,
    delay: Math.random() * 1.5,
    duration: Math.random() * 0.6 + 0.4
  }));

  const rightBars = Array.from({ length: 35 }).map((_, i) => ({
    id: i,
    height: Math.random() * 35 + 10,
    delay: Math.random() * 1.5,
    duration: Math.random() * 0.6 + 0.4
  }));

  return (
    <div className="flex items-center gap-6 z-10 relative">
      <div
        className="flex items-center justify-end gap-[3px] opacity-80 h-20 w-64"
        style={{ maskImage: 'linear-gradient(to left, black 0%, transparent 100%)', WebkitMaskImage: 'linear-gradient(to left, black 0%, transparent 100%)' }}
      >
         {leftBars.map(bar => (
            <motion.div
              key={`l-${bar.id}`}
              className="w-[2px] bg-cyan-400 rounded-none flex-shrink-0 shadow-[0_0_8px_rgba(34,211,238,0.6)]"
              animate={{ height: [`${bar.height * 0.4}px`, `${bar.height}px`, `${bar.height * 0.4}px`] }}
              transition={{ repeat: Infinity, duration: bar.duration, delay: bar.delay, ease: "easeInOut" }}
            />
         ))}
      </div>

      <div className="w-24 h-24 rounded border border-cyan-500/50 bg-slate-900/80 shadow-[0_0_30px_rgba(34,211,238,0.15)] flex items-center justify-center relative cursor-pointer hover:border-cyan-400 hover:shadow-[0_0_40px_rgba(34,211,238,0.25)] transition-all duration-300 shrink-0 group overflow-hidden">
         <div className="absolute inset-0 bg-cyan-500/5 group-hover:bg-cyan-500/10 transition-colors" />
         
         {/* Tech-y corner accents */}
         <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-cyan-400" />
         <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-cyan-400" />
         <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-cyan-400" />
         <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-cyan-400" />
         
         <div className="relative flex items-center justify-center z-10">
            <Mic size={32} className="text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)] group-hover:text-cyan-300 transition-colors" strokeWidth={1.5} />
         </div>
      </div>

      <div
        className="flex items-center gap-[3px] opacity-80 h-20 w-64"
        style={{ maskImage: 'linear-gradient(to right, black 0%, transparent 100%)', WebkitMaskImage: 'linear-gradient(to right, black 0%, transparent 100%)' }}
      >
         {rightBars.map(bar => (
            <motion.div
              key={`r-${bar.id}`}
              className="w-[2px] bg-cyan-400 rounded-none flex-shrink-0 shadow-[0_0_8px_rgba(34,211,238,0.6)]"
              animate={{ height: [`${bar.height * 0.4}px`, `${bar.height}px`, `${bar.height * 0.4}px`] }}
              transition={{ repeat: Infinity, duration: bar.duration, delay: bar.delay, ease: "easeInOut" }}
            />
         ))}
      </div>
    </div>
  );
}
