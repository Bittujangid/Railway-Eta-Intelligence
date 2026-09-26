import React, { useState } from 'react';
import { Search } from 'lucide-react';

export default function DynamicETATable({ trajectoryData }) {
  const [searchTerm, setSearchTerm] = useState('');

  if (!trajectoryData || !trajectoryData.trajectory) return null;

  const trajectory = trajectoryData.trajectory;
  const filtered = trajectory.filter(
    (st) =>
      st.station_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      st.station_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <section className="bg-white border border-[#D9E2EC] rounded-[10px] overflow-hidden h-full flex flex-col">
      {/* Subtle Blue-tinted Section Header */}
      <div className="bg-[#EEF3F8] border-b border-[#D9E2EC] px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[#102A56]">
            Station-wise dynamic ETA
          </h3>
          <p className="text-xs text-[#64748B]">
            Scheduled timetable vs dynamic forecasted arrival
          </p>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Filter stations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8 pr-3 py-1 text-xs bg-white border border-[#D9E2EC] rounded-[6px] text-[#172033] placeholder-[#64748B] focus:outline-none focus:ring-1 focus:ring-[#1F4B99] w-full sm:w-44"
          />
        </div>
      </div>

      {/* Railway Table Container */}
      <div className="overflow-x-auto overflow-y-auto max-h-[350px]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#F0F4F9] text-[#102A56] font-semibold sticky top-0 z-10 border-b border-[#D9E2EC] uppercase text-xs tracking-normal">
            <tr>
              <th className="py-2 px-3">#</th>
              <th className="py-2 px-3">Station</th>
              <th className="py-2 px-3">Scheduled</th>
              <th className="py-2 px-3 font-medium text-[#1F4B99]">Dynamic ETA</th>
              <th className="py-2 px-3">Delay</th>
              <th className="py-2 px-3 text-[#64748B]">ETA range</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#D9E2EC]/60">
            {filtered.slice(0, 50).map((st) => {
              const isHalt = st.is_commercial_halt;
              const delay = st.predicted_delay_minutes ?? 0;
              const delayClass =
                delay <= 5
                  ? 'text-gray-600 font-normal'
                  : delay <= 20
                  ? 'text-amber-700 font-medium'
                  : 'text-rose-700 font-semibold';

              return (
                <tr
                  key={st.station_id + st.station_sequence}
                  className={`hover:bg-[#EEF3F8]/60 transition-colors ${
                    isHalt ? 'bg-slate-50/50' : 'bg-white'
                  }`}
                >
                  <td className="py-2 px-3 text-[#64748B] text-xs">
                    {st.station_sequence}
                  </td>
                  <td className="py-2 px-3 font-medium text-[#172033]">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate max-w-[130px]" title={st.station_name}>
                        {st.station_name}
                      </span>
                      <span className="text-xs text-[#64748B]">[{st.station_id}]</span>
                      {isHalt && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-[5px] bg-blue-50 text-[#1F4B99] border border-blue-200 font-medium uppercase tracking-normal">
                          Halt
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 px-3 text-[#64748B] font-normal">
                    {st.scheduled_arrival || st.scheduled_departure || '—'}
                  </td>
                  <td className="py-2 px-3 font-medium text-[#102A56]">
                    {st.predicted_arrival_time}
                  </td>
                  <td className={`py-2 px-3 ${delayClass}`}>
                    +{delay.toFixed(0)}m
                  </td>
                  <td className="py-2 px-3 text-[#64748B] text-xs font-normal">
                    {st.eta_lower_bound} – {st.eta_upper_bound}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="p-2.5 text-xs text-[#64748B] border-t border-[#D9E2EC] bg-[#F4F7FA] text-right">
        Showing {Math.min(filtered.length, 50)} of {trajectory.length} route stops
      </div>
    </section>
  );
}
