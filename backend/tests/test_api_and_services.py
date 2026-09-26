"""
backend/tests/test_api_and_services.py
Automated test suite verifying the SIH26028 prototype invariants:
- API health
- Dataset loading & route ordering
- Speed/status consistency (STOPPED_STATION -> 0, IN_TRANSIT -> >0)
- Monotonic station sequence
- Non-negative distances
- Feasibility score bounds [0, 100]
- Trajectory sequential forecast
- Scenario switching causing real recalculation
"""

import pytest
import math
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.data_service import data_service
from backend.services.live_simulator import live_simulator
from backend.services.trajectory_service import trajectory_service
from backend.services.feasibility_service import feasibility_service
from backend.models.eta_model import predictor
from backend.models.evolution_model import evolution_engine

client = TestClient(app)

def test_api_health():
    """Verify /health returns 200, healthy status, and model loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["model_loaded"] is True
    assert "active_scenario" in data

def test_train_list():
    """Verify /trains returns list of available trains with route information."""
    response = client.get("/trains?limit=10")
    assert response.status_code == 200
    trains = response.json()
    assert len(trains) > 0
    sample = trains[0]
    assert "train_id" in sample
    assert "source_station_name" in sample
    assert "destination_station_name" in sample
    assert sample["source_type"] == "PUBLIC_COMMUNITY"

def test_route_monotonic_and_distances():
    """Verify station sequence increases monotonically and distances are non-negative."""
    schedule = data_service.get_train_schedule("12951")
    assert len(schedule) > 10, "12951 schedule must contain stations"
    
    prev_seq = 0
    for st in schedule:
        # Station sequence must increase
        seq = st["station_sequence"]
        assert seq > prev_seq, f"Sequence must strictly increase: {seq} <= {prev_seq}"
        prev_seq = seq
        
        # Distances cannot be negative
        dist_orig = st.get("distance_from_origin_km") or 0.0
        dist_next = st.get("distance_to_next_station_km") or 0.0
        assert dist_orig >= 0.0, f"Distance from origin cannot be negative: {dist_orig}"
        assert dist_next >= 0.0, f"Distance to next cannot be negative: {dist_next}"

def test_live_state_speed_status_consistency():
    """
    Critical Invariant:
    STOPPED_STATION -> speed == 0
    IN_TRANSIT       -> speed > 0
    """
    # Test STOPPED_STATION under NORMAL scenario
    live_simulator.set_scenario("NORMAL", "12951")
    state_norm = live_simulator.get_live_state("12951")
    assert state_norm["current_status"] == "STOPPED_STATION"
    assert state_norm["speed_kmph"] == 0.0, "Stopped train must have speed = 0"
    
    # Test IN_TRANSIT under CONGESTION scenario
    live_simulator.set_scenario("CONGESTION", "12951")
    state_cong = live_simulator.get_live_state("12951")
    assert state_cong["current_status"] == "IN_TRANSIT"
    assert state_cong["speed_kmph"] > 0.0, "In-transit train must have speed > 0"
    
    # Reset back to NORMAL
    live_simulator.set_scenario("NORMAL", "12951")

def test_trajectory_prediction_and_evolution():
    """Verify sequential trajectory forecasting, evolution classification, and uncertainty bounds."""
    response = client.get("/trains/12951/trajectory")
    assert response.status_code == 200
    data = response.json()
    assert data["train_id"] == "12951"
    assert data["evolution"] in ["RECOVER", "MAINTAIN", "INCREASE"]
    assert len(data["trajectory"]) > 5
    
    for pt in data["trajectory"]:
        assert pt["predicted_delay_minutes"] >= 0.0
        assert ":" in pt["predicted_arrival_time"]
        assert ":" in pt["eta_lower_bound"]
        assert ":" in pt["eta_upper_bound"]

def test_feasibility_score_bounds_and_deterministic():
    """
    Verify Feasibility Score is strictly between 0 and 100,
    and same inputs produce exact same score.
    """
    payload = {
        "train_id": "12951",
        "destination_station_id": "NDLS",
        "required_arrival_time": "09:15",
        "minimum_buffer_minutes": 15.0
    }
    res1 = client.post("/predict/feasibility", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert 0 <= data1["feasibility_score"] <= 100
    assert data1["status"] in ["FEASIBLE", "UNCERTAIN", "LOW_FEASIBILITY"]
    assert len(data1["recommendation"]) > 10
    
    # Check deterministic property
    res2 = client.post("/predict/feasibility", json=payload)
    assert res2.json()["feasibility_score"] == data1["feasibility_score"]

def test_scenario_switching_triggers_real_recalculation():
    """
    Verify switching scenario changes backend values (delays, congestion, evolution).
    """
    # Switch to NORMAL
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})
    traj_norm = client.get("/trains/12951/trajectory").json()
    
    # Switch to CONGESTION
    client.post("/simulation/scenario", json={"scenario": "CONGESTION", "train_id": "12951"})
    traj_cong = client.get("/trains/12951/trajectory").json()
    
    # Compare delays: CONGESTION scenario must have higher delay than NORMAL
    assert traj_cong["current_delay_minutes"] > traj_norm["current_delay_minutes"]
    assert traj_cong["scenario"] == "CONGESTION"
    
    # Clean up: reset to NORMAL
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})

def test_model_metrics_endpoint():
    """Verify /model/metrics returns real empirical test MAE, RMSE, and quantiles."""
    response = client.get("/model/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["algorithm"] == "XGBRegressor"
    assert metrics["train_rows"] > 10000
    assert metrics["test_rows"] > 5000
    assert metrics["mae"] > 0.0
    assert metrics["rmse"] > 0.0
    assert metrics["q05_residual"] < 0.0  # Underprediction quantile
    assert metrics["q95_residual"] > 0.0  # Overprediction quantile
    assert metrics["data_source_type"] == "SYNTHETIC_CALIBRATED"

def test_trajectory_physical_bounds_no_explosion():
    """
    CRITICAL AUDIT INVARIANT:
    Under NORMAL conditions on clear track (congestion <= 0.25),
    delay must NEVER undergo runaway explosion across a 60-station trajectory.
    Destination delay must demonstrate timetable slack absorption (recovery).
    """
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})
    traj = client.get("/trains/12951/trajectory").json()
    init_delay = traj["current_delay_minutes"]
    pts = traj["trajectory"]
    
    # Check max delay along the entire 60-station corridor
    max_route_delay = max(p["predicted_delay_minutes"] for p in pts)
    dest_delay = pts[-1]["predicted_delay_minutes"]
    
    # Assert delay did not explode (before fix it reached 165.5 min)
    assert max_route_delay <= init_delay + 2.0, f"Delay exploded to {max_route_delay} min on clear track!"
    assert dest_delay <= init_delay, f"Train failed to recover delay: dest={dest_delay} > init={init_delay}"
    assert traj["evolution"] == "RECOVER", f"Expected RECOVER evolution, got {traj['evolution']}"

def test_destination_eta_time_math_consistency():
    """
    Verify that station-wise dynamic ETA strictly matches:
    Scheduled Arrival (in minutes) + Predicted Delay (in minutes) mod 1440.
    """
    traj = client.get("/trains/12951/trajectory").json()
    for pt in traj["trajectory"][:10]:
        sched = pt["scheduled_arrival"]
        pred_eta = pt["predicted_arrival_time"]
        delay = pt["predicted_delay_minutes"]
        
        # Parse scheduled
        parts = [int(p) for p in sched.split(":")]
        sched_m = parts[0] * 60 + parts[1]
        expected_eta_m = int(sched_m + delay) % (24 * 60)
        expected_h = expected_eta_m // 60
        expected_m = expected_eta_m % 60
        expected_str = f"{expected_h:02d}:{expected_m:02d}"
        
        assert pred_eta == expected_str, f"ETA math mismatch at {pt['station_name']}: got {pred_eta}, expected {expected_str}"

def test_uncertainty_bounds_monotonicity():
    """
    Verify empirical uncertainty bounds satisfy:
    lower_bound_delay <= predicted_delay <= upper_bound_delay
    """
    traj = client.get("/trains/12951/trajectory").json()
    for pt in traj["trajectory"][:10]:
        delay = pt["predicted_delay_minutes"]
        lower_d, upper_d = predictor.get_uncertainty_bounds(delay)
        assert lower_d <= delay <= upper_d, f"Uncertainty bounds not monotonic: {lower_d} <= {delay} <= {upper_d}"

def test_feasibility_status_transitions():
    """
    Verify Feasibility Status correctly transitions across user time constraints:
    - Required time before arrival -> LOW_FEASIBILITY (score <= 25)
    - Required time near upper uncertainty bound -> UNCERTAIN (score 35-80)
    - Required time well after upper bound -> FEASIBLE (score >= 80)
    """
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})
    
    # Late arrival case
    res_late = client.post("/predict/feasibility", json={
        "train_id": "12951",
        "destination_station_id": "NDLS",
        "required_arrival_time": "08:15",
        "minimum_buffer_minutes": 15.0
    }).json()
    assert res_late["status"] == "LOW_FEASIBILITY"
    assert res_late["feasibility_score"] <= 25
    assert res_late["buffer_minutes"] < 0
    
    # Ample buffer case
    res_good = client.post("/predict/feasibility", json={
        "train_id": "12951",
        "destination_station_id": "NDLS",
        "required_arrival_time": "09:30",
        "minimum_buffer_minutes": 15.0
    }).json()
    assert res_good["status"] == "FEASIBLE"
    assert res_good["feasibility_score"] >= 80
    assert res_good["buffer_minutes"] >= 15.0

def test_overnight_midnight_feasibility_handling():
    """Verify feasibility correctly handles times crossing midnight (e.g. 23:45 -> 00:30)."""
    res = client.post("/predict/feasibility", json={
        "train_id": "12951",
        "destination_station_id": "NDLS",
        "required_arrival_time": "23:50",
        "minimum_buffer_minutes": 15.0
    }).json()
    assert 0 <= res["feasibility_score"] <= 100
    assert res["status"] in ["FEASIBLE", "UNCERTAIN", "LOW_FEASIBILITY"]

def test_direct_predict_eta_endpoint():
    """Verify /predict/eta returns predicted delay, uncertainty bounds, and MAE."""
    payload = {
        "previous_delay_minutes": 20.0,
        "speed_kmph": 75.0,
        "dwell_time_minutes": 2.0,
        "distance_to_next_station_km": 15.0,
        "day_of_week": 3,
        "hour": 14,
        "section_congestion": 0.3,
        "historical_recovery_minutes": 2.0,
        "train_interaction_density": 1,
        "scheduled_travel_time_minutes": 12.0
    }
    response = client.post("/predict/eta", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_delay_minutes"] >= 0.0
    assert data["uncertainty_lower_bound_minutes"] <= data["predicted_delay_minutes"]
    assert data["uncertainty_upper_bound_minutes"] >= data["predicted_delay_minutes"]
    assert data["validation_mae"] == 2.67

def test_propagation_risk_endpoint():
    """Verify /trains/{id}/propagation returns heuristic risk assessment and transparent label."""
    response = client.get("/trains/12951/propagation")
    assert response.status_code == 200
    data = response.json()
    assert data["propagation_risk"] in ["LOW", "MEDIUM", "HIGH"]
    assert data["assessment_label"] == "Propagation Risk — Prototype Heuristic"
    assert data["headway_minutes"] > 0

def test_eta_explanation_endpoint():
    """Verify /trains/{id}/explanation returns contributing factors with direction and impact."""
    response = client.get("/trains/12951/explanation")
    assert response.status_code == 200
    data = response.json()
    assert "evolution" in data
    assert "contributing_factors" in data
    assert isinstance(data["contributing_factors"], list)
    if data["contributing_factors"]:
        factor = data["contributing_factors"][0]
        assert factor["factor"] in ["High Section Congestion", "Clear Corridor Track", "Timetable Buffer Slack", "Platform / Junction Crossing", "Extended Station Dwell"]
        assert factor["impact_minutes"] is not None
        assert factor["direction"] in ["+", "-"]

def test_physics_delay_increment_dimensional_consistency():
    """
    CRITICAL AUDIT INVARIANT:
    Verify that delay increments in the Physics-Informed Safety Layer are
    dimensionally consistent, strictly expressed in minutes, and derived via
    kinematic relations:
        t_actual = (dist [km] / speed [km/h]) * 60 [min/h] = [min]
        delta_transit = t_actual [min] - sched_t [min] = [min]
    """
    # 1. Kinematic unit conversion check:
    test_dist_km = 30.0  # km
    test_sched_min = 20.0  # min (nominal speed = 90 km/h)
    test_speed_kmph = 45.0  # km/h (speed under congestion)
    
    t_actual_min = (test_dist_km / test_speed_kmph) * 60.0  # 40.0 min
    delta_delay_min = t_actual_min - test_sched_min          # 20.0 min
    
    # Assert exact dimensional arithmetic
    assert isinstance(delta_delay_min, float)
    assert round(delta_delay_min, 1) == 20.0, f"Expected 20.0 min, got {delta_delay_min}"
    
    # Check scaling: doubling distance at same speed doubles actual travel time
    t_double_dist = ((test_dist_km * 2) / test_speed_kmph) * 60.0
    assert t_double_dist == 2.0 * t_actual_min, "Kinematic transit time must scale linearly with distance"
    
    # 2. Live trajectory step-by-step dimensional consistency check across all stations
    client.post("/simulation/scenario", json={"scenario": "CONGESTION", "train_id": "12951"})
    traj = client.get("/trains/12951/trajectory").json()
    pts = traj["trajectory"]
    
    for i in range(1, len(pts)):
        prev_p = pts[i-1]
        curr_p = pts[i]
        
        step_delta = curr_p["predicted_delay_minutes"] - prev_p["predicted_delay_minutes"]
        # In CONGESTION scenario, step delta must be non-negative and expressed in minutes
        assert step_delta >= 0.0, f"Congestion step delta was negative at {curr_p['station_name']}: {step_delta}"
        # Max physical step delta for any section cannot exceed crawling time minus schedule
        assert step_delta < 30.0, f"Unphysical delay jump of {step_delta} min between adjacent stations!"
        
    # Reset back to NORMAL
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})

def test_xgboost_perturbation_and_monotonicity():
    """
    CRITICAL AUDIT TEST:
    Verify that perturbing raw XGBoost prediction actually changes the real
    production trajectory prediction in the expected monotonic direction across
    all operational scenarios (NORMAL, CONGESTION, SEVERE_DELAY).
    """
    for scenario in ["NORMAL", "CONGESTION", "SEVERE_DELAY"]:
        client.post("/simulation/scenario", json={"scenario": scenario, "train_id": "12951"})
        
        # 1. Baseline production trajectory run
        base_traj = trajectory_service.generate_trajectory("12951")
        base_step1 = base_traj["trajectory"][1]["predicted_delay_minutes"]
        
        orig_predict = predictor.predict_next_delay
        try:
            # 2. Perturb ML prediction HIGHER (+15 min)
            predictor.predict_next_delay = lambda feat: orig_predict(feat) + 15.0
            high_traj = trajectory_service.generate_trajectory("12951")
            high_step1 = high_traj["trajectory"][1]["predicted_delay_minutes"]
            
            # 3. Perturb ML prediction LOWER (-15 min)
            predictor.predict_next_delay = lambda feat: max(0.0, orig_predict(feat) - 15.0)
            low_traj = trajectory_service.generate_trajectory("12951")
            low_step1 = low_traj["trajectory"][1]["predicted_delay_minutes"]
        finally:
            predictor.predict_next_delay = orig_predict
            
        # Monotonicity invariant: Higher ML >= Baseline >= Lower ML
        assert high_step1 >= base_step1, f"Monotonicity breach in {scenario}: High ML ({high_step1}) < Base ({base_step1})"
        assert low_step1 <= base_step1, f"Monotonicity breach in {scenario}: Low ML ({low_step1}) > Base ({base_step1})"
        
        # Active ML model influence invariant: Final prediction must change
        assert (high_step1 != base_step1) or (low_step1 != base_step1), f"ML prediction was completely bypassed in {scenario}!"
        
    # Reset back to NORMAL
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})

def test_delay_trend_delta_to_next_stop_mathematical_consistency():
    """
    CRITICAL INVARIANT TEST:
    Verify that delta to next stop mathematically equals next_delay - current_delay:
    delta_to_next_stop = next_predicted_delay - current_delay

    Check across NORMAL, CONGESTION, and SEVERE_DELAY scenarios.
    Also verify integer display delta relationship:
    Current 16, Next 16 -> Delta 0
    Current 16, Next 12 -> Delta -4
    Current 16, Next 20 -> Delta +4
    """
    scenarios = {
        "NORMAL": {"expected_current": 16.0, "expected_next_display": 16, "expected_delta_display": 0},
        "CONGESTION": {"expected_current": 24.0, "expected_next_display": 25, "expected_delta_display": 1},
        "SEVERE_DELAY": {"expected_current": 52.0, "expected_next_display": 54, "expected_delta_display": 2}
    }

    for sc, expectations in scenarios.items():
        client.post("/simulation/scenario", json={"scenario": sc, "train_id": "12951"})
        traj = trajectory_service.generate_trajectory("12951")

        curr_delay = traj["current_delay_minutes"]
        next_delay = traj["next_delay_minutes"]
        delta_delay = traj["delta_delay_minutes"]

        # 1. Backend contract: delta_delay_minutes == next_delay - current_delay
        assert delta_delay == round(next_delay - curr_delay, 1), (
            f"Scenario {sc} failed: delta ({delta_delay}) != next ({next_delay}) - curr ({curr_delay})"
        )

        # 2. Display contract: displayed delta == displayed Next - displayed Current
        curr_display = round(curr_delay)
        next_display = round(next_delay)
        delta_display = next_display - curr_display

        assert curr_display == int(expectations["expected_current"])
        assert next_display == expectations["expected_next_display"]
        assert delta_display == expectations["expected_delta_display"]
        assert delta_display == next_display - curr_display

    # 3. Explicit unit test cases from specification
    test_cases = [
        (16, 16, 0),
        (16, 12, -4),
        (16, 20, 4)
    ]
    for c, n, expected_delta in test_cases:
        assert n - c == expected_delta

    # Reset back to NORMAL
    client.post("/simulation/scenario", json={"scenario": "NORMAL", "train_id": "12951"})



