import React from 'react';

export default function PropagationRiskCard({ propagationData }) {
  if (!propagationData) return null;

  const {
    propagation_risk = 'LOW',
    headway_minutes = 20,
    train_interaction_density = 1,
    downstream_impacted_trains = 0,
    assessment_label = 'Prototype heuristic'
  } = propagationData;

  const riskBadge =
    propagation_risk === 'HIGH'
      ? 'bg-rose-50 text-rose-800 border-rose-300'
      : propagation_risk === 'MEDIUM'
      ? 'bg-amber-50 text-amber-800 border-amber-300'
      : 'bg-emerald-50 text-emerald-800 border-emerald-300';

  return (
    <section className="bg-white border border-[#D9E2EC] rounded-[10px] overflow-hidden h-full flex flex-col justify-between">
      {/* Subtle Blue-tinted Header */}
      <div className="bg-[#EEF3F8] border-b border-[#D9E2EC] px-4 py-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#102A56]">
            Network impact
          </h3>
          <p className="text-xs text-[#64748B]">
            Corridor interaction and delay propagation
          </p>
        </div>
        <span className="text-xs text-[#64748B] bg-white px-2 py-0.5 rounded-[5px] border border-[#D9E2EC]">
          {assessment_label}
        </span>
      </div>

      <div className="p-4 flex-1 space-y-2.5 text-xs">
        <div className="flex items-center justify-between py-1.5 border-b border-gray-100">
          <span className="text-[#64748B] font-normal">Propagation risk</span>
          <span className={`font-medium px-2 py-0.5 rounded-[5px] text-xs border ${riskBadge}`}>
            {propagation_risk}
          </span>
        </div>

        <div className="flex items-center justify-between py-1.5 border-b border-gray-100">
          <span className="text-[#64748B] font-normal">Scheduled headway</span>
          <span className="font-semibold text-[#172033]">
            {headway_minutes.toFixed(0)} min
          </span>
        </div>

        <div className="flex items-center justify-between py-1.5 border-b border-gray-100">
          <span className="text-[#64748B] font-normal">Interaction density</span>
          <span className="font-semibold text-[#172033]">
            {train_interaction_density} trains/section
          </span>
        </div>

        <div className="flex items-center justify-between py-1.5">
          <span className="text-[#64748B] font-normal">Connected train risk</span>
          <span className="font-semibold text-[#172033]">
            {downstream_impacted_trains} potential delays
          </span>
        </div>
      </div>

      <div className="p-2.5 text-xs text-[#64748B] border-t border-[#D9E2EC] bg-[#F4F7FA]">
        Calculated from timetable headway intervals and section train density
      </div>
    </section>
  );
}
