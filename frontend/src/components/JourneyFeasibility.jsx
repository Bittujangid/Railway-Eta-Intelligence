import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';
import { evaluateFeasibility } from '../services/api';

export default function JourneyFeasibility({ trainId, trajectoryData }) {
  const terminus = trajectoryData?.trajectory?.[trajectoryData.trajectory.length - 1];
  const defaultDestId = terminus?.station_id || 'NDLS';

  function addMinutesToTime(timeStr, mins) {
    if (!timeStr) return '09:00';
    const [h, m] = timeStr.split(':').map(Number);
    const total = (h * 60 + m + mins) % (24 * 60);
    const nh = Math.floor(total / 60);
    const nm = total % 60;
    return `${String(nh).padStart(2, '0')}:${String(nm).padStart(2, '0')}`;
  }

  const [destId, setDestId] = useState(defaultDestId);
  const [reqTime, setReqTime] = useState('09:00');
  const [minBuffer, setMinBuffer] = useState(15);
  const [loading, setLoading] = useState(false);
  const [feasibilityResult, setFeasibilityResult] = useState(null);

  useEffect(() => {
    if (terminus) {
      setDestId(terminus.station_id);
      setReqTime(addMinutesToTime(terminus.predicted_arrival_time, 25));
    }
  }, [terminus?.station_id, terminus?.predicted_arrival_time]);

  useEffect(() => {
    if (!trainId || !destId || !reqTime) return;
    runEvaluation();
  }, [trainId, destId, reqTime, minBuffer, trajectoryData?.scenario]);

  async function runEvaluation() {
    setLoading(true);
    try {
      const res = await evaluateFeasibility(trainId, destId, reqTime, minBuffer);
      setFeasibilityResult(res);
    } catch (err) {
      console.error('Feasibility calculation error:', err);
    } finally {
      setLoading(false);
    }
  }

  const score = feasibilityResult?.feasibility_score ?? 85;
  const status = feasibilityResult?.status ?? 'FEASIBLE';

  const statusConfig =
    status === 'FEASIBLE'
      ? {
          title: 'FEASIBLE',
          color: 'text-emerald-800 bg-emerald-50 border-emerald-300',
          icon: CheckCircle2,
          iconColor: 'text-emerald-600'
        }
      : status === 'UNCERTAIN'
      ? {
          title: 'UNCERTAIN',
          color: 'text-amber-800 bg-amber-50 border-amber-300',
          icon: AlertTriangle,
          iconColor: 'text-amber-600'
        }
      : {
          title: 'LOW FEASIBILITY',
          color: 'text-rose-800 bg-rose-50 border-rose-300',
          icon: AlertOctagon,
          iconColor: 'text-rose-600'
        };

  const StatusIcon = statusConfig.icon;

  return (
    <section className="bg-white border border-[#D9E2EC] rounded-[10px] overflow-hidden">
      {/* Subtle Blue-tinted Section Header */}
      <div className="bg-[#EEF3F8] border-b border-[#D9E2EC] px-4 sm:px-5 py-3.5">
        <h2 className="text-base font-semibold text-[#102A56]">
          Can I reach on time?
        </h2>
        <p className="text-xs text-[#64748B]">
          Passenger journey feasibility evaluated against dynamic arrival forecast and safety buffer
        </p>
      </div>

      <div className="p-4 sm:p-5">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-stretch">
          {/* Left: Input Form (5 cols) */}
          <div className="md:col-span-5 space-y-3 bg-[#EEF3F8] border border-[#D9E2EC] rounded-[8px] p-4">
            <div>
              <label htmlFor="feas-dest" className="block text-xs font-medium text-[#172033] mb-1">
                Destination station
              </label>
              <select
                id="feas-dest"
                value={destId}
                onChange={(e) => setDestId(e.target.value)}
                className="w-full bg-white border border-[#D9E2EC] rounded-[6px] px-3 py-1.5 text-xs text-[#172033] focus:outline-none focus:ring-1 focus:ring-[#1F4B99] cursor-pointer"
              >
                {trajectoryData?.trajectory?.map((st) => (
                  <option key={st.station_id} value={st.station_id}>
                    {st.station_name} [{st.station_id}]
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="feas-req-time" className="block text-xs font-medium text-[#172033] mb-1">
                  Required arrival
                </label>
                <input
                  id="feas-req-time"
                  type="time"
                  value={reqTime}
                  onChange={(e) => setReqTime(e.target.value)}
                  className="w-full bg-white border border-[#D9E2EC] rounded-[6px] px-3 py-1.5 text-xs text-[#172033] focus:outline-none focus:ring-1 focus:ring-[#1F4B99]"
                />
              </div>

              <div>
                <label htmlFor="feas-buffer" className="block text-xs font-medium text-[#172033] mb-1">
                  Min buffer (min)
                </label>
                <input
                  id="feas-buffer"
                  type="number"
                  min="0"
                  max="180"
                  value={minBuffer}
                  onChange={(e) => setMinBuffer(e.target.value)}
                  className="w-full bg-white border border-[#D9E2EC] rounded-[6px] px-3 py-1.5 text-xs text-[#172033] focus:outline-none focus:ring-1 focus:ring-[#1F4B99]"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={runEvaluation}
              disabled={loading}
              className="w-full mt-1 bg-[#1F4B99] hover:bg-[#102A56] text-white text-xs font-medium py-2 px-4 rounded-[6px] transition-colors"
            >
              {loading ? 'Evaluating...' : 'Check journey feasibility'}
            </button>
          </div>

          {/* Right: Decision Status & Recommendation (7 cols) */}
          <div className="md:col-span-7 flex flex-col justify-between space-y-3">
            {/* Decision Status Bar */}
            <div className={`p-3.5 rounded-[8px] border flex items-center justify-between ${statusConfig.color}`}>
              <div className="flex items-center gap-3">
                <StatusIcon className={`w-6 h-6 ${statusConfig.iconColor}`} />
                <div>
                  <span className="text-xs font-medium text-[#64748B] uppercase tracking-normal block">
                    Feasibility decision
                  </span>
                  <span className="text-base font-semibold">
                    {statusConfig.title}
                  </span>
                </div>
              </div>

              <div className="text-right">
                <span className="text-xs text-[#64748B] block">Available buffer</span>
                <span className="text-lg font-semibold">
                  {feasibilityResult?.buffer_minutes ?? 0} min
                </span>
              </div>
            </div>

            {/* Metric details row */}
            <div className="grid grid-cols-3 gap-2 bg-[#EEF3F8] border border-[#D9E2EC] rounded-[8px] p-2.5 text-xs">
              <div>
                <span className="text-[#64748B] block text-xs">Predicted arrival</span>
                <span className="font-semibold text-[#102A56]">
                  {feasibilityResult?.predicted_eta ?? '--:--'}
                </span>
              </div>
              <div>
                <span className="text-[#64748B] block text-xs">Required by</span>
                <span className="font-semibold text-[#172033]">
                  {reqTime}
                </span>
              </div>
              <div>
                <span className="text-[#64748B] block text-xs">Feasibility score</span>
                <span className="font-medium text-[#64748B]">
                  {score}/100
                </span>
              </div>
            </div>

            {/* Recommendation Box with very light blue-gray background */}
            <div className="bg-[#EEF3F8] border border-[#D9E2EC] rounded-[8px] p-3 text-xs text-[#172033] leading-relaxed">
              <strong className="text-[#102A56] font-semibold block mb-0.5">Recommendation:</strong>
              {feasibilityResult?.recommendation || 'Evaluating connection and arrival timing...'}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
