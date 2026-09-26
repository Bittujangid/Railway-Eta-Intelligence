import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CurrentTrainState from './components/CurrentTrainState';
import TrajectoryHeroChart from './components/TrajectoryHeroChart';
import DynamicETATable from './components/DynamicETATable';
import JourneyFeasibility from './components/JourneyFeasibility';
import WhyETAChanged from './components/WhyETAChanged';
import PropagationRiskCard from './components/PropagationRiskCard';
import RouteMap from './components/RouteMap';
import DataProvenance from './components/DataProvenance';

import {
  fetchTrains,
  fetchLiveState,
  fetchTrajectory,
  fetchPropagation,
  fetchModelMetrics,
  updateScenario
} from './services/api';

export default function App() {
  const [trains, setTrains] = useState([]);
  const [selectedTrainId, setSelectedTrainId] = useState('12951');
  const [activeScenario, setActiveScenario] = useState('NORMAL');
  const [loadingScenario, setLoadingScenario] = useState(false);

  const [liveState, setLiveState] = useState(null);
  const [trajectoryData, setTrajectoryData] = useState(null);
  const [propagationData, setPropagationData] = useState(null);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load train master list and ML validation metrics
  useEffect(() => {
    async function init() {
      try {
        const [trainsRes, metricsRes] = await Promise.all([
          fetchTrains().catch(() => []),
          fetchModelMetrics().catch(() => null)
        ]);
        setTrains(trainsRes);
        setModelMetrics(metricsRes);

        if (trainsRes.length > 0) {
          const has12951 = trainsRes.some((t) => t.train_id === '12951');
          if (!has12951) {
            setSelectedTrainId(trainsRes[0].train_id);
          }
        }
      } catch (err) {
        console.error('Initialization error:', err);
      }
    }
    init();
  }, []);

  // Reload train telemetry, trajectory, and propagation when trainId changes
  useEffect(() => {
    if (!selectedTrainId) return;
    loadTrainData(selectedTrainId);
  }, [selectedTrainId]);

  async function loadTrainData(trainId) {
    setLoading(true);
    try {
      const [liveRes, trajRes, propRes] = await Promise.all([
        fetchLiveState(trainId),
        fetchTrajectory(trainId),
        fetchPropagation(trainId)
      ]);
      setLiveState(liveRes);
      setTrajectoryData(trajRes);
      setPropagationData(propRes);
      if (liveRes?.scenario) {
        setActiveScenario(liveRes.scenario);
      }
    } catch (err) {
      console.error('Failed to load train data:', err);
    } finally {
      setLoading(false);
    }
  }

  // Real backend scenario change handler
  async function handleSelectScenario(scenario) {
    if (scenario === activeScenario) return;
    setLoadingScenario(true);
    try {
      await updateScenario(scenario, selectedTrainId);
      setActiveScenario(scenario);
      await loadTrainData(selectedTrainId);
    } catch (err) {
      console.error('Failed to update scenario:', err);
    } finally {
      setLoadingScenario(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F4F7FA] text-[#172033] flex flex-col font-sans">
      {/* Top Navigation */}
      <Header
        trains={trains}
        selectedTrainId={selectedTrainId}
        onSelectTrain={(id) => setSelectedTrainId(id)}
        activeScenario={activeScenario}
        onSelectScenario={handleSelectScenario}
        loadingScenario={loadingScenario}
      />

      {/* Main Application Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* A. Current Train Summary Bar */}
        <CurrentTrainState liveState={liveState} />

        {/* B. Primary Hero: Arrival Forecast & Trajectory */}
        <TrajectoryHeroChart trajectoryData={trajectoryData} metrics={modelMetrics} />

        {/* C. Dynamic ETA Table & Live Route Map */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-7">
            <DynamicETATable trajectoryData={trajectoryData} />
          </div>
          <div className="lg:col-span-5">
            <RouteMap liveState={liveState} trajectoryData={trajectoryData} />
          </div>
        </div>

        {/* D. Passenger Journey Feasibility ("Can I reach on time?") */}
        <JourneyFeasibility trainId={selectedTrainId} trajectoryData={trajectoryData} />

        {/* E. Supporting Operational Insights */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
          <WhyETAChanged trainId={selectedTrainId} scenario={activeScenario} />
          <PropagationRiskCard propagationData={propagationData} />
        </div>

        {/* F. Data & Model Transparency */}
        <DataProvenance metrics={modelMetrics} />
      </main>
    </div>
  );
}
