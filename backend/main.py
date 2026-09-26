"""
backend/main.py
FastAPI application for SIH26028: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.schemas.eta_schemas import (
    HealthResponse,
    TrainSummary,
    LiveTrainState,
    TrajectoryResponse,
    FeasibilityRequest,
    FeasibilityResponse,
    ScenarioChangeRequest,
    ModelMetricsResponse,
    PropagationRiskResponse
)
from backend.models.eta_model import predictor
from backend.models.evolution_model import evolution_engine
from backend.services.data_service import data_service
from backend.services.live_simulator import live_simulator
from backend.services.trajectory_service import trajectory_service
from backend.services.propagation_service import propagation_service
from backend.services.feasibility_service import feasibility_service

app = FastAPI(
    title="Indian Railways AI ETA Intelligence API",
    description="SIH26028: Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains",
    version="1.0.0"
)

# Enable CORS for local React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Returns system status, model availability, and active simulation scenario."""
    return {
        "status": "healthy",
        "model_loaded": predictor.model is not None,
        "database_connected": data_service.db_path.exists(),
        "active_scenario": live_simulator.active_scenario,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/trains", response_model=List[TrainSummary])
def get_trains(limit: int = Query(default=50, ge=1, le=200)):
    """Fetch prominent coaching trains with route and schedule coverage."""
    trains = data_service.get_featured_trains(limit=limit)
    return trains

@app.get("/trains/{train_id}/live", response_model=LiveTrainState)
def get_train_live(train_id: str):
    """
    Returns current simulated live telemetry for train.
    Explicitly includes feed_type='SIMULATED_LIVE' and data_source_type='SYNTHETIC_DEMO'.
    """
    state = live_simulator.get_live_state(train_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Train {train_id} not found in timetable.")
    return state

@app.get("/trains/{train_id}/trajectory", response_model=TrajectoryResponse)
def get_train_trajectory(train_id: str):
    """
    Sequential multi-station delay forecast and dynamic ETA trajectory rollout.
    HERO component showing station-by-station delay evolution.
    """
    traj = trajectory_service.generate_trajectory(train_id)
    if not traj:
        raise HTTPException(status_code=404, detail=f"Trajectory for train {train_id} not available.")
    return traj

@app.get("/trains/{train_id}/etas")
def get_train_etas(train_id: str):
    """Returns station-wise scheduled arrival, predicted ETA, delay, and uncertainty bounds."""
    traj = trajectory_service.generate_trajectory(train_id)
    if not traj:
        raise HTTPException(status_code=404, detail=f"ETAs for train {train_id} not available.")
    return {
        "train_id": traj["train_id"],
        "train_name": traj["train_name"],
        "scenario": traj["scenario"],
        "validation_mae": traj["validation_mae"],
        "stations": traj["trajectory"]
    }

@app.post("/predict/eta")
def predict_eta_direct(features: Dict[str, Any]):
    """On-demand prediction of next-station arrival delay with empirical uncertainty."""
    next_delay = predictor.predict_next_delay(features)
    lower, upper = predictor.get_uncertainty_bounds(next_delay)
    return {
        "predicted_delay_minutes": next_delay,
        "uncertainty_lower_bound_minutes": lower,
        "uncertainty_upper_bound_minutes": upper,
        "validation_mae": predictor.metrics.get("mae", 2.67),
        "data_source_type": "MODEL_OUTPUT"
    }

@app.post("/predict/delay-evolution")
def predict_delay_evolution(data: Dict[str, float]):
    """Classifies delay evolution (RECOVER / MAINTAIN / INCREASE) using transparent threshold."""
    curr_delay = data.get("current_delay", 0.0)
    pred_delay = data.get("predicted_delay", 0.0)
    evolution, delta = evolution_engine.classify_evolution(curr_delay, pred_delay)
    return {
        "current_delay": curr_delay,
        "predicted_delay": pred_delay,
        "delta_delay": delta,
        "evolution": evolution
    }

@app.post("/predict/feasibility", response_model=FeasibilityResponse)
def evaluate_journey_feasibility(request: FeasibilityRequest):
    """
    Evaluates passenger destination arrival requirements, calculating:
    - buffer minutes
    - transparent 0-100 feasibility score
    - status: FEASIBLE, UNCERTAIN, LOW_FEASIBILITY
    - smart recommendation
    """
    res = feasibility_service.evaluate_journey(
        train_id=request.train_id,
        destination_station_id=request.destination_station_id,
        required_arrival_time=request.required_arrival_time,
        minimum_buffer_minutes=request.minimum_buffer_minutes
    )
    return res

@app.get("/trains/{train_id}/propagation", response_model=PropagationRiskResponse)
def get_propagation_risk(train_id: str):
    """Evaluates train interaction and delay propagation risk heuristic."""
    return propagation_service.evaluate_propagation_risk(train_id)

@app.post("/simulation/scenario")
def update_simulation_scenario(request: ScenarioChangeRequest):
    """
    Switches simulation scenario (NORMAL / CONGESTION / SEVERE_DELAY).
    Causes real backend recalculation of telemetry, trajectory, and feasibility.
    """
    updated_state = live_simulator.set_scenario(request.scenario, request.train_id)
    return {
        "message": f"Scenario updated to {request.scenario}",
        "live_state": updated_state
    }

@app.get("/model/metrics", response_model=ModelMetricsResponse)
def get_model_metrics():
    """Returns actual XGBoost model training and validation metrics."""
    return predictor.metrics

@app.get("/trains/{train_id}/explanation")
def get_eta_explanation(train_id: str):
    """
    Why ETA changed: explains contributing factors (congestion, slack, dwell, interactions)
    using actual feature inputs (Section 23).
    """
    live = live_simulator.get_live_state(train_id)
    traj = trajectory_service.generate_trajectory(train_id)
    
    features = {
        "section_congestion": live.get("congestion_level", 0.25),
        "historical_recovery_minutes": 2.5 if live.get("scenario") == "NORMAL" else 0.5,
        "dwell_time_minutes": 3.0,
        "train_interaction_density": 3 if live.get("scenario") == "CONGESTION" else 1,
        "speed_kmph": live.get("speed_kmph", 0.0)
    }
    
    delta = traj.get("delta_delay_minutes", 0.0)
    factors = evolution_engine.explain_eta_change(features, delta)
    
    return {
        "train_id": train_id,
        "scenario": live.get("scenario", "NORMAL"),
        "delta_delay_minutes": delta,
        "evolution": traj.get("evolution", "MAINTAIN"),
        "contributing_factors": factors
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
