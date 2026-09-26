import React from 'react';
import { TrendingDown, TrendingUp, Minus, ArrowRight } from 'lucide-react';

export default function DelayEvolutionCard({ trajectoryData }) {
  if (!trajectoryData) return null;

  const {
    current_delay_minutes = 0,
    next_delay_minutes = 0,
    evolution = 'MAINTAIN'
  } = trajectoryData;

  const currentVal = Math.round(current_delay_minutes);
  const nextVal = Math.round(next_delay_minutes);
  const delta_delay_minutes = nextVal - currentVal;

  const isRecover = evolution === 'RECOVER';
  const isIncrease = evolution === 'INCREASE';
  const isMaintain = evolution === 'MAINTAIN';

  const badgeColor = isRecover
    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
    : isIncrease
    ? 'bg-rose-500/10 border-rose-500/40 text-rose-400'
    : 'bg-amber-500/10 border-amber-500/40 text-amber-400';

  const statusTitleColor = isRecover
    ? 'text-emerald-400'
    : isIncrease
    ? 'text-rose-400'
    : 'text-amber-400';

  return (
    <section className="bg-slate-900/80 border border-slate-800 rounded-[10px] p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-300">
              SECTION 2 — Delay Evolution
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Threshold: &plusmn;3.0 min
          </span>
        </div>

        {/* Large Status Badge */}
        <div className={`mt-2 p-4 rounded-[8px] border flex items-center justify-between ${badgeColor}`}>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-[6px] bg-slate-950/60 shadow-inner">
              {isRecover && <TrendingDown className="w-7 h-7 text-emerald-400" />}
              {isIncrease && <TrendingUp className="w-7 h-7 text-rose-400" />}
              {isMaintain && <Minus className="w-7 h-7 text-amber-400" />}
            </div>
            <div>
              <div className="text-xs uppercase tracking-normal text-slate-400 font-semibold">
                Trajectory Trend
              </div>
              <div className={`text-2xl font-bold tracking-tight ${statusTitleColor}`}>
                {evolution}
              </div>
            </div>
          </div>

          <div className="text-right">
            <div className="text-xs text-slate-400">Delay Change (&Delta;)</div>
            <div className={`text-2xl font-mono font-bold ${
              delta_delay_minutes < 0 ? 'text-emerald-400' : delta_delay_minutes > 0 ? 'text-rose-400' : 'text-slate-300'
            }`}>
              {delta_delay_minutes > 0 ? `+${delta_delay_minutes.toFixed(1)}` : delta_delay_minutes.toFixed(1)} min
            </div>
          </div>
        </div>
      </div>

      {/* Step by step delay transition */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="bg-slate-800/40 p-2 rounded-lg">
          <span className="text-slate-400 block mb-0.5">Current Delay</span>
          <span className="font-mono font-bold text-white text-sm">
            +{currentVal} min
          </span>
        </div>
        <div className="flex items-center justify-center text-slate-500">
          <ArrowRight className="w-4 h-4 text-cyan-400 animate-pulse" />
        </div>
        <div className="bg-slate-800/40 p-2 rounded-lg">
          <span className="text-slate-400 block mb-0.5">Next Station Delay</span>
          <span className="font-mono font-bold text-white text-sm">
            +{nextVal} min
          </span>
        </div>
      </div>
    </section>
  );
}
