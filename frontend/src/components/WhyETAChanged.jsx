import React, { useEffect, useState } from 'react';
import { fetchExplanation } from '../services/api';

export default function WhyETAChanged({ trainId, scenario }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!trainId) return;
    setLoading(true);
    fetchExplanation(trainId)
      .then((data) => setExplanation(data))
      .catch((err) => console.error('Explanation fetch error:', err))
      .finally(() => setLoading(false));
  }, [trainId, scenario]);

  const factors = explanation?.contributing_factors || [];

  return (
    <section className="bg-white border border-[#D9E2EC] rounded-[10px] overflow-hidden h-full flex flex-col justify-between">
      {/* Subtle Blue-tinted Header */}
      <div className="bg-[#EEF3F8] border-b border-[#D9E2EC] px-4 py-3">
        <h3 className="text-sm font-semibold text-[#102A56]">
          Why did the ETA change?
        </h3>
        <p className="text-xs text-[#64748B]">
          Operational factors driving the delay forecast
        </p>
      </div>

      <div className="p-4 flex-1">
        {factors.length === 0 ? (
          <div className="py-6 text-center text-xs text-gray-400">
            Normal operating conditions with no significant delay variance.
          </div>
        ) : (
          <div className="space-y-2.5 text-xs">
            {factors.map((f, idx) => {
              const isPositive = f.direction === '+';
              const absVal = Math.abs(f.impact_minutes);
              const barWidth = Math.min(100, Math.max(15, (absVal / 7.0) * 100));

              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-[#172033]">
                    <span className="font-medium">{f.factor}</span>
                    <span
                      className={`font-semibold text-xs ${
                        isPositive ? 'text-amber-800' : 'text-emerald-700'
                      }`}
                    >
                      {isPositive ? `+${f.impact_minutes}` : f.impact_minutes} min
                    </span>
                  </div>

                  {/* Horizontal Contribution Bar */}
                  <div className="w-full bg-[#EEF3F8] h-1.5 rounded-[3px] overflow-hidden">
                    <div
                      className={`h-full rounded-[3px] ${
                        isPositive ? 'bg-amber-600' : 'bg-emerald-600'
                      }`}
                      style={{ width: `${barWidth}%` }}
                    ></div>
                  </div>

                  <p className="text-xs text-[#64748B] leading-normal">
                    {f.description}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="p-2.5 text-xs text-[#64748B] border-t border-[#D9E2EC] bg-[#F4F7FA]">
        Evaluated from section congestion, track crossing, and timetable buffer rules
      </div>
    </section>
  );
}
