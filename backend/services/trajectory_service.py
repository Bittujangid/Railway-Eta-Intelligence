"""
backend/services/trajectory_service.py
Sequential multi-station delay and dynamic ETA trajectory generator.
Rolls out dynamic predictions over all upcoming stations until destination.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from backend.models.eta_model import predictor
from backend.models.evolution_model import evolution_engine
from backend.services.data_service import data_service
from backend.services.live_simulator import live_simulator

def parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    if not time_str or time_str == "None":
        return None
    try:
        parts = [int(p) for p in time_str.split(":")]
        return parts[0] * 60 + parts[1]
    except Exception:
        return None

def minutes_to_time_str(total_minutes: int) -> str:
    norm = int(total_minutes) % (24 * 60)
    h = norm // 60
    m = norm % 60
    return f"{h:02d}:{m:02d}"

class TrajectoryService:
    def generate_trajectory(self, train_id: str, scenario_override: Optional[str] = None) -> Dict[str, Any]:
        live_state = live_simulator.get_live_state(train_id)
        if not live_state:
            return {}

        scenario = scenario_override or live_state.get("scenario", "NORMAL")
        congestion_level = float(live_state.get("congestion_level", 0.25))
        current_delay = float(live_state.get("delay_minutes", 16.0))
        current_seq = live_state.get("current_station_sequence", 1)

        schedule = data_service.get_train_schedule(train_id)
        if not schedule:
            return {}

        # Filter upcoming stations from current sequence onwards
        upcoming_stations = [s for s in schedule if s["station_sequence"] >= current_seq]
        if not upcoming_stations:
            upcoming_stations = schedule[-5:]

        trajectory_points = []
        sim_delay = current_delay
        cum_distance = 0.0

        # Empirical residual bounds from validation test set
        val_mae = predictor.metrics.get("mae", 2.67)
        next_delay = sim_delay

        for idx, st in enumerate(upcoming_stations):
            dist_next = float(st.get("distance_to_next_station_km") or 10.0)
            sched_arr = st.get("scheduled_arrival") or st.get("scheduled_departure") or "12:00:00"
            sched_dep = st.get("scheduled_departure")
            sched_arr_mins = parse_time_to_minutes(sched_arr) or 720

            # For the first station (current station), delay is observed current delay
            if idx == 0:
                pred_delay = current_delay
            else:
                prev_st = upcoming_stations[idx - 1]
                dist = float(prev_st.get("distance_to_next_station_km") or 10.0)
                
                # Accurately parse scheduled travel time (preventing falsy '0.0 or 25.0' bug)
                sched_t_raw = prev_st.get("scheduled_travel_time_minutes")
                if sched_t_raw is not None and float(sched_t_raw) > 0:
                    sched_t = float(sched_t_raw)
                else:
                    sched_t = max(3.0, round((dist / 75.0) * 60.0, 1))

                # Accurately parse scheduled dwell (preventing falsy '0.0 or 2.0' bug)
                dwell_raw = prev_st.get("dwell_time_minutes")
                dwell = float(dwell_raw) if dwell_raw is not None else 0.0

                # Section timetable slack (engineering recovery allowance)
                # Timetable allows recovery when operating near line MPS (120 km/h)
                min_physical_t = (dist / 120.0) * 60.0
                sec_slack = max(0.2, sched_t - min_physical_t)

                # Scenario-aligned transit parameters
                if scenario == "NORMAL":
                    transit_speed = 95.0
                    hist_rec = round(sec_slack * 0.8, 1)
                    interactions = 1
                elif scenario == "CONGESTION":
                    transit_speed = 48.0
                    hist_rec = round(sec_slack * 0.3, 1)
                    interactions = 3
                else:
                    transit_speed = 30.0
                    hist_rec = round(sec_slack * 0.1, 1)
                    interactions = 4

                hour_raw = prev_st.get("hour")
                hour = int(hour_raw) if hour_raw is not None else 12

                features = {
                    "previous_delay_minutes": sim_delay,
                    "speed_kmph": float(live_state.get("speed_kmph", transit_speed)) if (idx == 1 and live_state.get("speed_kmph", 0.0) > 0) else transit_speed,
                    "dwell_time_minutes": dwell,
                    "distance_to_next_station_km": dist,
                    "day_of_week": int(prev_st.get("day") or 3) % 7 + 1,
                    "hour": hour,
                    "section_congestion": congestion_level,
                    "historical_recovery_minutes": hist_rec,
                    "train_interaction_density": interactions,
                    "scheduled_travel_time_minutes": sched_t
                }

                raw_pred = predictor.predict_next_delay(features)

                # Physics-informed section bounds on autoregressive transition:
                # 1. Kinematic bounds and running times (all explicitly in minutes):
                # Minimum running time at corridor line MPS (120 km/h) [min]
                # Maximum running time under cautionary crawl at 25 km/h [min]
                max_crawl_t = (dist / 25.0) * 60.0
                max_gain = max(0.5, max_crawl_t - sched_t)

                # 2. Kinematic transit time under section congestion:
                # Nominal scheduled speed: v_nom = dist / (sched_t / 60) [km/h]
                # Effective speed degraded by congestion factor alpha: v_eff = v_nom * (1 - 0.28 * C) [km/h]
                nominal_speed = (dist / (sched_t / 60.0)) if sched_t > 0 else 75.0
                speed_factor = max(0.40, 1.0 - 0.28 * congestion_level)
                effective_speed = max(25.0, min(120.0, nominal_speed * speed_factor))
                
                # Actual transit time: t_actual = (dist / effective_speed) * 60 [minutes]
                t_actual = (dist / effective_speed) * 60.0
                delta_transit = t_actual - sched_t  # [minutes] - [minutes] = [minutes]

                # 3. Primary XGBoost dynamic prediction:
                raw_ml_delta = raw_pred - sim_delay

                # 4. Physics-Informed Fusion & Guardrail Constraints:
                # The ML model provides the continuous predictive signal;
                # the physics layer enforces railway kinematic constraints and time conservation.
                if congestion_level <= 0.30:
                    # Clear corridor: train utilizes available section slack to absorb delay
                    # Base kinematic recovery from section timetable slack
                    r_base = min(sim_delay, sec_slack * 0.45)
                    # ML recovery factor: higher raw_ml_delta -> lower recovery -> higher final delay (strictly monotonic)
                    alpha_ml = max(0.20, min(1.80, 1.0 - 0.50 * ((raw_ml_delta - 1.90) / 8.0)))
                    fused_delta = - (r_base * alpha_ml)
                    
                    # Physical bounds: cannot recover more than total section slack, cannot gain delay on clear track
                    delta_min = -min(sim_delay, sec_slack)
                    delta_max = 0.0
                    constrained_delta = max(delta_min, min(delta_max, fused_delta))
                elif congestion_level >= 0.70:
                    # Congested corridor: ML model predicts delay accumulation based on interaction density & congestion
                    # ML modulation factor: higher raw_ml_delta -> higher modulation -> higher delay gain (strictly monotonic)
                    m_ml = max(0.20, min(2.50, 0.50 + 0.50 * (raw_ml_delta / 8.0)))
                    fused_delta = delta_transit * m_ml
                    
                    # Physical bounds: minimum step increase 0.20m, maximum caution crawl
                    delta_min = 0.20
                    delta_max = max_gain
                    constrained_delta = max(delta_min, min(delta_max, fused_delta))
                else:
                    # Moderate corridor: blend ML delta with kinematic delta
                    fused_delta = 0.50 * max(0.0, raw_ml_delta * 0.30) + 0.50 * max(0.0, delta_transit) * 0.30
                    constrained_delta = max(0.0, min(max_gain, fused_delta))

                pred_delay = max(0.0, round(sim_delay + constrained_delta, 1))
                sim_delay = pred_delay
                if idx == 1:
                    next_delay = pred_delay

            # Dynamic ETA arrival time calculation
            pred_arr_mins = sched_arr_mins + pred_delay
            eta_str = minutes_to_time_str(pred_arr_mins)

            # Uncertainty bounds calculation using empirical validation residuals
            lower_delay, upper_delay = predictor.get_uncertainty_bounds(pred_delay)
            eta_lower_mins = sched_arr_mins + lower_delay
            eta_upper_mins = sched_arr_mins + upper_delay

            eta_lower_str = minutes_to_time_str(eta_lower_mins)
            eta_upper_str = minutes_to_time_str(eta_upper_mins)

            trajectory_points.append({
                "station_sequence": int(st["station_sequence"]),
                "station_id": st["station_id"],
                "station_name": st["station_name"],
                "scheduled_arrival": sched_arr[:5] if sched_arr else None,
                "scheduled_departure": sched_dep[:5] if sched_dep else None,
                "scheduled_delay_minutes": 0.0,
                "predicted_delay_minutes": round(pred_delay, 1),
                "predicted_arrival_time": eta_str,
                "eta_lower_bound": eta_lower_str,
                "eta_upper_bound": eta_upper_str,
                "distance_from_current_km": round(cum_distance, 1),
                "latitude": st.get("latitude"),
                "longitude": st.get("longitude"),
                "is_commercial_halt": bool(st.get("is_commercial_halt", False))
            })

            cum_distance += dist_next

        # Determine macro journey-level evolution to destination
        dest_delay = trajectory_points[-1]["predicted_delay_minutes"] if trajectory_points else current_delay
        evolution_status, _ = evolution_engine.classify_evolution(current_delay, dest_delay)

        # Delta to next stop: strictly Next Delay - Current Delay (mathematically consistent with UI)
        delta_to_next = round(float(next_delay - current_delay), 1)

        # Destination info
        dest_station = upcoming_stations[-1]["station_name"] if upcoming_stations else "Terminus"
        curr_station = live_state.get("current_station_name", "Current")

        return {
            "train_id": str(train_id),
            "train_name": live_state.get("train_name", ""),
            "current_station": curr_station,
            "destination_station": dest_station,
            "current_delay_minutes": float(current_delay),
            "next_delay_minutes": float(next_delay),
            "delta_delay_minutes": float(delta_to_next),
            "evolution": evolution_status,
            "scenario": scenario,
            "data_source_type": "MODEL_OUTPUT",
            "validation_mae": float(val_mae),
            "trajectory": trajectory_points
        }

trajectory_service = TrajectoryService()
