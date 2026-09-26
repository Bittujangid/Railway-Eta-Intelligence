import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';

export default function TrajectoryHeroChart({ trajectoryData, metrics }) {
  const [filterMajor, setFilterMajor] = useState(false);

  if (!trajectoryData || !trajectoryData.trajectory || trajectoryData.trajectory.length === 0) {
    return (
      <div className="bg-white border border-[#D9E2EC] rounded-lg p-6 text-center text-xs text-gray-500">
        Loading arrival forecast and trajectory...
      </div>
    );
  }

  const allPoints = trajectoryData.trajectory;
  const currentDelay = trajectoryData.current_delay_minutes ?? 0;
  const terminus = allPoints[allPoints.length - 1];

  const destinationName = trajectoryData.destination_station || terminus.station_name;
  const destinationCode = terminus.station_id;
  const predictedArrival = terminus.predicted_arrival_time;
  const finalDelay = terminus.predicted_delay_minutes;
  const rangeLower = terminus.eta_lower_bound;
  const rangeUpper = terminus.eta_upper_bound;
  const valMae = metrics?.mae ?? trajectoryData.validation_mae ?? 2.67;

  // Evolution & next stop delay details
  const evolution = trajectoryData.evolution || 'MAINTAIN';
  const nextDelay = trajectoryData.next_delay_minutes ?? (allPoints[1]?.predicted_delay_minutes ?? currentDelay);
  const currentVal = Math.round(currentDelay);
  const nextVal = Math.round(nextDelay);
  const deltaDelay = nextVal - currentVal;

  const evolutionLabel =
    evolution === 'RECOVER'
      ? '↘ Recovering'
      : evolution === 'INCREASE'
      ? '↗ Increasing'
      : '→ Stable';

  const evolutionBadge =
    evolution === 'RECOVER'
      ? 'text-emerald-700 bg-emerald-50 border-emerald-300'
      : evolution === 'INCREASE'
      ? 'text-rose-700 bg-rose-50 border-rose-300'
      : 'text-amber-700 bg-amber-50 border-amber-300';

  // Filter stations if toggled
  const displayPoints = filterMajor
    ? allPoints.filter((p, idx) => p.is_commercial_halt || idx === 0 || idx === allPoints.length - 1)
    : allPoints;

  const chartData = displayPoints.map((p, idx) => ({
    name: p.station_name,
    code: p.station_id,
    sequence: p.station_sequence,
    predictedDelay: p.predicted_delay_minutes,
    scheduledArrival: p.scheduled_arrival || '--',
    predictedETA: p.predicted_arrival_time,
    etaLower: p.eta_lower_bound,
    etaUpper: p.eta_upper_bound,
    isCurrent: idx === 0
  }));

  const maxDelay = Math.max(...chartData.map((d) => d.predictedDelay), currentDelay, 15);
  const yDomainMax = Math.ceil((maxDelay + 10) / 10) * 10;

  return (
    <section className="bg-white border border-[#D9E2EC] rounded-[10px] overflow-hidden">
      {/* 1. Subtle blue-tinted card header area */}
      <div className="bg-[#EEF3F8] border-b border-[#D9E2EC] px-4 sm:px-5 py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-[#102A56]">
            Arrival forecast
          </h2>
          <p className="text-xs text-[#64748B]">
            Expected arrival and delay evolution across the remaining journey
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setFilterMajor(!filterMajor)}
            className={`px-2.5 py-1 text-xs rounded-[6px] border transition-colors ${
              filterMajor
                ? 'bg-[#1F4B99] text-white border-[#1F4B99] font-medium'
                : 'bg-white border-[#D9E2EC] text-[#172033] hover:bg-gray-50'
            }`}
          >
            {filterMajor ? 'Showing major halts' : 'Show major halts only'}
          </button>
          <span className="text-xs text-[#64748B] bg-white px-2 py-0.5 rounded-[5px] border border-[#D9E2EC]">
            {chartData.length} stops
          </span>
        </div>
      </div>

      <div className="p-4 sm:p-5 space-y-4">
        {/* 2. Top Summary Row with Clear Visual Weight */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3.5">
          {/* Main Destination & Forecast Metrics (8 cols) */}
          <div className="md:col-span-8 bg-[#EEF3F8] border border-[#D9E2EC] rounded-[8px] p-3.5 grid grid-cols-2 sm:grid-cols-4 gap-3 items-center">
            {/* Destination */}
            <div className="space-y-0.5">
              <span className="text-xs font-medium text-[#64748B] uppercase tracking-normal block">
                Destination
              </span>
              <div className="text-sm font-semibold text-[#172033] truncate" title={destinationName}>
                {destinationName}
              </div>
              <span className="text-xs text-[#64748B]">[{destinationCode}]</span>
            </div>

            {/* Most Important: Predicted Arrival */}
            <div className="space-y-0.5">
              <span className="text-xs font-semibold text-[#1F4B99] uppercase tracking-normal block">
                Predicted arrival
              </span>
              <div className="text-2xl sm:text-3xl font-semibold text-[#102A56] leading-none">
                {predictedArrival}
              </div>
              <span className="text-xs text-[#64748B] block mt-0.5">
                Sched: {terminus.scheduled_arrival || '--:--'}
              </span>
            </div>

            {/* Second: Expected Delay */}
            <div className="space-y-0.5">
              <span className="text-xs font-medium text-[#64748B] uppercase tracking-normal block">
                Expected delay
              </span>
              <div className={`text-xl font-semibold leading-none ${
                finalDelay <= 10 ? 'text-emerald-700' : finalDelay <= 30 ? 'text-amber-700' : 'text-rose-700'
              }`}>
                +{finalDelay.toFixed(0)} min
              </div>
              <span className="text-xs text-[#64748B] block mt-0.5">At destination</span>
            </div>

            {/* Supporting: Likely Range */}
            <div className="space-y-0.5">
              <span className="text-xs font-medium text-[#64748B] uppercase tracking-normal block">
                Likely range
              </span>
              <div className="text-xs font-medium text-[#172033]">
                {rangeLower} – {rangeUpper}
              </div>
              <span className="text-xs text-[#64748B] block">
                MAE: {valMae} min
              </span>
            </div>
          </div>

          {/* Right: Delay Trend (4 cols) */}
          <div className="md:col-span-4 bg-[#EEF3F8] border border-[#D9E2EC] rounded-[8px] p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#64748B] uppercase tracking-normal">
                Delay trend
              </span>
              <span className={`px-2 py-0.5 rounded-[5px] text-xs font-medium border ${evolutionBadge}`}>
                {evolutionLabel}
              </span>
            </div>

            <div className="my-1 flex items-baseline gap-2">
              <span className="text-xl font-semibold text-[#172033]">
                {deltaDelay > 0 ? `+${deltaDelay.toFixed(1)}` : deltaDelay.toFixed(1)} min
              </span>
              <span className="text-xs text-[#64748B]">delta to next stop</span>
            </div>

            <div className="text-xs text-[#64748B] flex justify-between border-t border-[#D9E2EC] pt-1.5">
              <span>Current: <strong className="text-[#172033] font-medium">+{currentVal}m</strong></span>
              <span>Next: <strong className="text-[#172033] font-medium">+{nextVal}m</strong></span>
            </div>
          </div>
        </div>

        {/* 3. Future Delay Trajectory Chart */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-[#172033] uppercase">
              Expected delay across remaining journey
            </h3>
            <span className="text-xs text-[#64748B]">
              Forecast updates as current operating conditions change
            </span>
          </div>

          <div className="h-60 w-full bg-white border border-[#D9E2EC] rounded-[8px] p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 12, right: 20, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />

                <XAxis
                  dataKey="code"
                  stroke="#94A3B8"
                  tick={{ fill: '#64748B', fontSize: 11, fontFamily: '"IBM Plex Sans", Arial, Helvetica, sans-serif' }}
                  interval={chartData.length > 20 ? Math.floor(chartData.length / 10) : 0}
                  angle={-20}
                  textAnchor="end"
                  height={30}
                />

                <YAxis
                  stroke="#94A3B8"
                  domain={[0, yDomainMax]}
                  tick={{ fill: '#64748B', fontSize: 11, fontFamily: '"IBM Plex Sans", Arial, Helvetica, sans-serif' }}
                  unit="m"
                />

                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white border border-[#D9E2EC] rounded-[6px] p-2.5 text-xs min-w-[190px]">
                          <div className="font-semibold text-[#102A56] border-b border-gray-100 pb-1 mb-1 flex justify-between">
                            <span className="truncate max-w-[120px]">{data.name}</span>
                            <span className="text-[#1F4B99]">[{data.code}]</span>
                          </div>
                          <div className="space-y-0.5 text-gray-600">
                            <div className="flex justify-between">
                              <span>Predicted delay:</span>
                              <span className="font-semibold text-[#172033]">+{data.predictedDelay} min</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Scheduled arrival:</span>
                              <span className="text-gray-500">{data.scheduledArrival}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Predicted ETA:</span>
                              <span className="font-semibold text-[#1F4B99]">{data.predictedETA}</span>
                            </div>
                            <div className="flex justify-between text-[11px] text-[#64748B] pt-1 border-t border-gray-100 mt-1">
                              <span>Likely range:</span>
                              <span>{data.etaLower} – {data.etaUpper}</span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />

                {/* Current delay reference line */}
                <ReferenceLine
                  y={currentDelay}
                  stroke="#D97706"
                  strokeDasharray="4 4"
                  label={{
                    value: `Current: +${currentDelay.toFixed(0)}m`,
                    fill: '#B45309',
                    fontSize: 11,
                    fontFamily: '"IBM Plex Sans", Arial, Helvetica, sans-serif',
                    position: 'right'
                  }}
                />

                {/* Dominant Railway Blue Forecast Line */}
                <Line
                  type="monotone"
                  dataKey="predictedDelay"
                  stroke="#1F4B99"
                  strokeWidth={2.5}
                  dot={{ r: 2.5, fill: '#1F4B99', stroke: '#FFFFFF', strokeWidth: 1.5 }}
                  activeDot={{ r: 5, fill: '#102A56' }}
                  name="Predicted delay"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Clean Legend */}
          <div className="flex items-center justify-between text-xs text-[#64748B] pt-2">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-[#1F4B99] inline-block"></span>
                <span className="text-[#172033] font-medium">Predicted delay trajectory</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3.5 h-0.5 bg-[#D97706] border-b border-dashed border-[#D97706] inline-block"></span>
                <span>Current delay baseline</span>
              </span>
            </div>
            <span className="text-xs text-[#64748B]">
              Sequential XGBoost rollout
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
