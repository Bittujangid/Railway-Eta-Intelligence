import React from 'react';

export default function CurrentTrainState({ liveState }) {
  if (!liveState) {
    return (
      <div className="bg-white border border-[#D9E2EC] rounded-lg p-4 text-center text-xs text-gray-500">
        Loading current train telemetry...
      </div>
    );
  }

  const isStopped = liveState.current_status === 'STOPPED_STATION';
  const delayMinutes = liveState.delay_minutes ?? 0;

  // Semantic delay color
  const delayColor =
    delayMinutes <= 5
      ? 'text-emerald-700'
      : delayMinutes <= 25
      ? 'text-amber-700'
      : 'text-rose-700';

  return (
    <div className="bg-white border border-[#D9E2EC] rounded-[10px] p-4">
      {/* Subtle Section Header */}
      <div className="flex items-center justify-between border-b border-gray-100 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-3.5 bg-[#1F4B99] rounded-[2px] inline-block"></span>
          <span className="text-xs font-semibold text-[#1F4B99] uppercase tracking-normal">
            Current Train
          </span>
        </div>
        <div className="text-xs text-[#64748B]">
          Feed: <strong className="text-[#172033] font-medium">{liveState.feed_type}</strong>
        </div>
      </div>

      {/* Five Values in Horizontal Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5 sm:divide-x sm:divide-[#D9E2EC]/70">
        {/* 1. Current Station */}
        <div className="space-y-0.5">
          <span className="text-xs font-medium text-[#64748B] block">
            Current station
          </span>
          <div className="text-sm font-semibold text-[#172033] truncate" title={liveState.current_station_name}>
            {liveState.current_station_name || '—'}
          </div>
          <p className="text-xs text-[#64748B]">
            {liveState.current_station_id} • Seq #{liveState.current_station_sequence}
          </p>
        </div>

        {/* 2. Next Station */}
        <div className="space-y-0.5 sm:pl-3.5">
          <span className="text-xs font-medium text-[#64748B] block">
            Next station
          </span>
          <div className="text-sm font-semibold text-[#172033] truncate" title={liveState.next_station_name}>
            {liveState.next_station_name || '—'}
          </div>
          <p className="text-xs text-[#64748B]">
            {liveState.next_station_id} • {liveState.distance_to_next_station_km} km
          </p>
        </div>

        {/* 3. Current Delay */}
        <div className="space-y-0.5 sm:pl-3.5">
          <span className="text-xs font-medium text-[#64748B] block">
            Current delay
          </span>
          <div className={`text-xl font-semibold ${delayColor}`}>
            +{delayMinutes.toFixed(0)} <span className="text-xs font-normal text-[#64748B]">min</span>
          </div>
          <p className="text-xs text-[#64748B]">
            Observed delay
          </p>
        </div>

        {/* 4. Speed & Traffic */}
        <div className="space-y-0.5 sm:pl-3.5">
          <span className="text-xs font-medium text-[#64748B] block">
            Speed
          </span>
          <div className="text-xl font-semibold text-[#172033]">
            {liveState.speed_kmph?.toFixed(0) ?? '0'}{' '}
            <span className="text-xs font-normal text-[#64748B]">km/h</span>
          </div>
          <p className="text-xs text-[#64748B]">
            Section traffic: {(liveState.congestion_level * 100).toFixed(0)}%
          </p>
        </div>

        {/* 5. Status */}
        <div className="space-y-0.5 sm:pl-3.5 col-span-2 sm:col-span-1">
          <span className="text-xs font-medium text-[#64748B] block">
            Status
          </span>
          <div className="pt-0.5">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-[5px] text-xs font-medium border ${
                isStopped
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-200'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                  isStopped ? 'bg-amber-500' : 'bg-emerald-600'
                }`}
              ></span>
              {isStopped ? 'Stopped at station' : 'In transit'}
            </span>
          </div>
          <p className="text-xs text-[#64748B] truncate mt-0.5" title={liveState.section_condition}>
            {liveState.section_condition ? liveState.section_condition.replace(/_/g, ' ').toLowerCase() : 'Clear track'}
          </p>
        </div>
      </div>
    </div>
  );
}
