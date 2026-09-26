"""
backend/schemas/eta_schemas.py
Pydantic response and request models for SIH26028 Railway ETA prototype.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database_connected: bool
    active_scenario: str
    timestamp: str

class TrainSummary(BaseModel):
    train_id: str
    train_name: str
    train_type: Optional[str] = None
    source_station_id: str
    source_station_name: str
    destination_station_id: str
    destination_station_name: str
    distance_km: Optional[float] = None
    duration_hours: Optional[float] = None
    source_type: str = "PUBLIC_COMMUNITY"

class LiveTrainState(BaseModel):
    train_id: str
    train_name: str
    current_station_id: str
    current_station_name: str
    current_station_sequence: int
    latitude: float
    longitude: float
    delay_minutes: float
    speed_kmph: float
    current_status: str  # STOPPED_STATION or IN_TRANSIT
    next_station_id: str
    next_station_name: str
    distance_to_next_station_km: float
    congestion_level: float
    section_condition: str
    scenario: str
    timestamp: str
    feed_type: str = "SIMULATED_LIVE"
    data_source_type: str = "SYNTHETIC_DEMO"

class TrajectoryStationPoint(BaseModel):
    station_sequence: int
    station_id: str
    station_name: str
    scheduled_arrival: Optional[str] = None
    scheduled_departure: Optional[str] = None
    scheduled_delay_minutes: float
    predicted_delay_minutes: float
    predicted_arrival_time: str
    eta_lower_bound: str
    eta_upper_bound: str
    distance_from_current_km: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_commercial_halt: bool = False

class TrajectoryResponse(BaseModel):
    train_id: str
    train_name: str
    current_station: str
    destination_station: str
    current_delay_minutes: float
    next_delay_minutes: float
    delta_delay_minutes: float
    evolution: str  # RECOVER, MAINTAIN, INCREASE
    scenario: str
    data_source_type: str
    validation_mae: float
    trajectory: List[TrajectoryStationPoint]

class FeasibilityRequest(BaseModel):
    train_id: str
    destination_station_id: str
    required_arrival_time: str  # Format HH:MM or HH:MM:SS
    minimum_buffer_minutes: float = Field(default=15.0, ge=0.0)

class FeasibilityResponse(BaseModel):
    train_id: str
    destination_station_id: str
    destination_station_name: str
    scheduled_arrival: str
    predicted_eta: str
    eta_lower: str
    eta_upper: str
    required_arrival: str
    buffer_minutes: float
    minimum_buffer_minutes: float
    feasibility_score: int
    status: str  # FEASIBLE, UNCERTAIN, LOW_FEASIBILITY
    recommendation: str
    uncertainty_range_minutes: float
    data_source_type: str = "MODEL_OUTPUT"

class ScenarioChangeRequest(BaseModel):
    scenario: str = Field(..., description="NORMAL, CONGESTION, or SEVERE_DELAY")
    train_id: Optional[str] = None

class ModelMetricsResponse(BaseModel):
    algorithm: str
    features: List[str]
    target: str
    train_rows: int
    test_rows: int
    train_date_range: str
    test_date_range: str
    mae: float
    rmse: float
    q05_residual: float
    q95_residual: float
    data_source_type: str
    feature_importances: Dict[str, float]
    uncertainty_method: str

class PropagationRiskResponse(BaseModel):
    train_id: str
    current_station: str
    next_station: str
    propagation_risk: str  # LOW, MEDIUM, HIGH
    headway_minutes: float
    train_interaction_density: int
    section_congestion: float
    downstream_impacted_trains: int
    assessment_label: str = "Propagation Risk — Prototype Heuristic"
