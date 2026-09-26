import React from 'react';
import { Train } from 'lucide-react';

export default function Header({
  trains,
  selectedTrainId,
  onSelectTrain,
  activeScenario,
  onSelectScenario,
  loadingScenario
}) {
  return (
    <header className="bg-[#102A56] text-white border-b border-[#0D2246] sticky top-0 z-40 h-[64px] flex items-center">
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Left: Brand & Badges */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-[6px] bg-[#1F4B99] text-white flex items-center justify-center">
            <Train className="w-4 h-4" />
          </div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-[17px] font-semibold text-white tracking-normal">
              Railway ETA Intelligence
            </h1>
            <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-[5px] bg-[#1A3B73] text-blue-100 border border-[#2B5292]">
              SIH26028
            </span>
            <span className="hidden sm:inline-flex items-center text-[11px] font-normal px-2 py-0.5 rounded-[5px] bg-[#183464] text-slate-300 border border-[#28487D]">
              Simulated live feed
            </span>
          </div>
        </div>

        {/* Right: Train Selector & Scenario Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Train Selector */}
          <div className="flex items-center gap-2">
            <label htmlFor="train-select" className="text-xs font-medium text-slate-300">
              Train
            </label>
            <select
              id="train-select"
              value={selectedTrainId}
              onChange={(e) => onSelectTrain(e.target.value)}
              className="bg-white text-[#172033] text-xs font-medium rounded-[6px] px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#1F4B99] cursor-pointer max-w-[240px] truncate border border-slate-200"
            >
              {trains.map((t) => (
                <option key={t.train_id} value={t.train_id}>
                  {t.train_id} — {t.train_name}
                </option>
              ))}
            </select>
          </div>

          {/* Scenario Segmented Control */}
          <div className="flex items-center bg-[#0C2145] p-0.5 rounded-[6px] border border-[#1C3B6E]">
            <span className="text-[11px] font-medium text-slate-300 px-2">
              Scenario
            </span>
            <button
              type="button"
              onClick={() => onSelectScenario('NORMAL')}
              disabled={loadingScenario}
              className={`px-2.5 py-1 text-xs font-medium rounded-[5px] transition-colors ${
                activeScenario === 'NORMAL'
                  ? 'bg-white text-emerald-800 font-semibold'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Normal
            </button>
            <button
              type="button"
              onClick={() => onSelectScenario('CONGESTION')}
              disabled={loadingScenario}
              className={`px-2.5 py-1 text-xs font-medium rounded-[5px] transition-colors ${
                activeScenario === 'CONGESTION'
                  ? 'bg-white text-amber-800 font-semibold'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Congestion
            </button>
            <button
              type="button"
              onClick={() => onSelectScenario('SEVERE_DELAY')}
              disabled={loadingScenario}
              className={`px-2.5 py-1 text-xs font-medium rounded-[5px] transition-colors ${
                activeScenario === 'SEVERE_DELAY'
                  ? 'bg-white text-rose-800 font-semibold'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Severe delay
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
