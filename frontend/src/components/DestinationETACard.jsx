import React from 'react';
import { Flag, Clock, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function DestinationETACard({ trajectoryData, metrics }) {
  if (!trajectoryData || !trajectoryData.trajectory || trajectoryData.trajectory.length === 0) return null;

  const terminus = trajectoryData.trajectory[trajectoryData.trajectory.length - 1];
  const destName = trajectoryData.destination_station || terminus.station_name;
  const destCode = terminus.station_id;
  const predETA = terminus.predicted_arrival_time;
  const lowerRange = terminus.eta_lower_bound;
  const upperRange = terminus.eta_upper_bound;
  const finalDelay = terminus.predicted_delay_minutes;
  const valMae = metrics?.mae ?? trajectoryData.validation_mae ?? 2.67;

  return (
    <section className="bg-gradient-to-br from-slate-900 via-slate-900 to-cyan-950/40 border border-cyan-500/30 rounded-2xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              SECTION 5 — Destination ETA
            </h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-semibold">
            AI Rollout
          </span>
        </div>

        {/* Destination Station */}
        <div className="flex items-center gap-2.5 text-slate-300 mb-2">
          <Flag className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-semibold truncate" title={destName}>
            {destName} <span className="font-mono text-cyan-400">[{destCode}]</span>
          </span>
        </div>

        {/* Large Predicted ETA */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 my-2 text-center">
          <span className="text-xs uppercase tracking-wider text-slate-400 block mb-1">
            Predicted Destination Arrival
          </span>
          <div className="text-4xl font-black font-mono tracking-tight text-white flex items-center justify-center gap-2">
            <Clock className="w-7 h-7 text-cyan-400" />
            {predETA}
          </div>
          <div className="text-xs font-mono text-amber-300 mt-1">
            Expected arrival delay: +{finalDelay.toFixed(1)} min
          </div>
        </div>
      </div>

      {/* Uncertainty Interval & Validation MAE */}
      <div className="mt-3 pt-3 border-t border-slate-800 grid grid-cols-2 gap-2.5 text-xs">
        <div className="bg-slate-800/50 p-2.5 rounded-lg">
          <span className="text-slate-400 block text-[11px] mb-0.5">Likely Range (Q05–Q95)</span>
          <span className="font-mono font-bold text-slate-200">
            {lowerRange} – {upperRange}
          </span>
        </div>
        <div className="bg-slate-800/50 p-2.5 rounded-lg">
          <span className="text-slate-400 block text-[11px] mb-0.5">Validation MAE</span>
          <span className="font-mono font-bold text-cyan-300">
            {valMae} min
          </span>
        </div>
      </div>
    </section>
  );
}
