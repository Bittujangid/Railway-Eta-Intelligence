/**
 * API client for interacting with the FastAPI Railway ETA backend.
 */

const BASE_URL = 'http://127.0.0.1:8000';

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}

export async function fetchTrains() {
  const res = await fetch(`${BASE_URL}/trains?limit=30`);
  if (!res.ok) throw new Error('Failed to fetch trains');
  return res.json();
}

export async function fetchLiveState(trainId) {
  const res = await fetch(`${BASE_URL}/trains/${trainId}/live`);
  if (!res.ok) throw new Error(`Failed to fetch live state for ${trainId}`);
  return res.json();
}

export async function fetchTrajectory(trainId) {
  const res = await fetch(`${BASE_URL}/trains/${trainId}/trajectory`);
  if (!res.ok) throw new Error(`Failed to fetch trajectory for ${trainId}`);
  return res.json();
}

export async function fetchPropagation(trainId) {
  const res = await fetch(`${BASE_URL}/trains/${trainId}/propagation`);
  if (!res.ok) throw new Error(`Failed to fetch propagation risk for ${trainId}`);
  return res.json();
}

export async function fetchExplanation(trainId) {
  const res = await fetch(`${BASE_URL}/trains/${trainId}/explanation`);
  if (!res.ok) throw new Error(`Failed to fetch explanation for ${trainId}`);
  return res.json();
}

export async function fetchModelMetrics() {
  const res = await fetch(`${BASE_URL}/model/metrics`);
  if (!res.ok) throw new Error('Failed to fetch model metrics');
  return res.json();
}

export async function updateScenario(scenario, trainId) {
  const res = await fetch(`${BASE_URL}/simulation/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario, train_id: trainId })
  });
  if (!res.ok) throw new Error('Failed to update scenario');
  return res.json();
}

export async function evaluateFeasibility(trainId, destinationStationId, requiredArrivalTime, minimumBufferMinutes) {
  const res = await fetch(`${BASE_URL}/predict/feasibility`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      train_id: trainId,
      destination_station_id: destinationStationId,
      required_arrival_time: requiredArrivalTime,
      minimum_buffer_minutes: parseFloat(minimumBufferMinutes)
    })
  });
  if (!res.ok) throw new Error('Failed to evaluate feasibility');
  return res.json();
}
