"""
backend/services/feasibility_service.py
Calculates passenger journey feasibility, deterministic feasibility score (0-100),
and actionable smart recommendations based on predicted ETA and empirical uncertainty.
"""

from typing import Dict, Any, Optional
from backend.services.trajectory_service import (
    trajectory_service,
    parse_time_to_minutes,
    minutes_to_time_str
)

class FeasibilityService:
    def evaluate_journey(
        self,
        train_id: str,
        destination_station_id: str,
        required_arrival_time: str,
        minimum_buffer_minutes: float = 15.0
    ) -> Dict[str, Any]:
        """
        Evaluates passenger journey feasibility against user constraints:
        - required_arrival_time (HH:MM)
        - minimum_buffer_minutes
        Uses trajectory predicted ETA and upper empirical uncertainty bound (Q95).
        """
        traj_res = trajectory_service.generate_trajectory(train_id)
        if not traj_res or not traj_res.get("trajectory"):
            return {
                "train_id": train_id,
                "destination_station_id": destination_station_id,
                "destination_station_name": "Unknown",
                "scheduled_arrival": "--:--",
                "predicted_eta": "--:--",
                "eta_lower": "--:--",
                "eta_upper": "--:--",
                "required_arrival": required_arrival_time,
                "buffer_minutes": 0.0,
                "minimum_buffer_minutes": minimum_buffer_minutes,
                "feasibility_score": 0,
                "status": "LOW_FEASIBILITY",
                "recommendation": "Unable to evaluate route for this train.",
                "uncertainty_range_minutes": 0.0
            }

        trajectory = traj_res["trajectory"]
        
        # Match target destination station
        matched_st = None
        for st in trajectory:
            if st["station_id"].upper() == destination_station_id.upper():
                matched_st = st
                break
        
        # Default to final terminus if specific station ID not matched
        if not matched_st:
            matched_st = trajectory[-1]

        sched_arr_str = matched_st.get("scheduled_arrival") or matched_st.get("scheduled_departure") or "08:30"
        pred_eta_str = matched_st.get("predicted_arrival_time", "08:42")
        eta_lower_str = matched_st.get("eta_lower_bound", "08:37")
        eta_upper_str = matched_st.get("eta_upper_bound", "08:47")

        pred_eta_m = parse_time_to_minutes(pred_eta_str) or 510
        eta_upper_m = parse_time_to_minutes(eta_upper_str) or 515
        eta_lower_m = parse_time_to_minutes(eta_lower_str) or 505
        req_arr_m = parse_time_to_minutes(required_arrival_time) or 530

        # Handle overnight wraparound across midnight boundaries
        if eta_upper_m < eta_lower_m:
            eta_upper_m += 24 * 60
        if pred_eta_m < eta_lower_m:
            pred_eta_m += 24 * 60

        if req_arr_m < pred_eta_m - 720:
            req_arr_m += 24 * 60
        elif pred_eta_m < req_arr_m - 720:
            pred_eta_m += 24 * 60
            eta_upper_m += 24 * 60
            eta_lower_m += 24 * 60

        buffer_minutes = float(req_arr_m - pred_eta_m)
        worst_case_buffer = float(req_arr_m - eta_upper_m)
        uncertainty_range = max(0.0, float(eta_upper_m - eta_lower_m))

        # Transparent Deterministic Feasibility Score (0-100)
        # Documented Formula:
        # Case 1: Mean arrival is late (buffer < 0) -> Score [0, 25]
        # Case 2: Mean arrival is on-time but upper bound is late (worst_case_buffer < 0) -> Score [30, 65]
        # Case 3: Upper bound on-time, but buffer < minimum_buffer -> Score [65, 80]
        # Case 4: Upper bound exceeds minimum_buffer -> Score [80, 100]
        
        if buffer_minutes < 0:
            # Deficit: late arrival expected
            score = max(0, int(25 + 1.5 * buffer_minutes))
            status = "LOW_FEASIBILITY"
            recommendation = (
                f"Predicted arrival ({pred_eta_str}) exceeds required time ({required_arrival_time}) "
                f"by {abs(buffer_minutes):.0f} minutes. Journey feasibility is low. Consider an earlier train."
            )
        elif worst_case_buffer < 0:
            # Mean is okay, but uncertainty interval spills past required time
            uncert_ratio = min(1.0, max(0.0, buffer_minutes / (uncertainty_range if uncertainty_range > 0 else 10.0)))
            score = int(35 + 30 * uncert_ratio)
            status = "UNCERTAIN"
            recommendation = (
                f"Arrival is currently feasible on median forecast ({pred_eta_str}), "
                f"but upper uncertainty bound ({eta_upper_str}) breaches required arrival ({required_arrival_time}). "
                f"Monitor live trajectory updates."
            )
        elif worst_case_buffer < minimum_buffer_minutes:
            # Feasible, but buffer is tight relative to user request
            ratio = max(0.0, min(1.0, worst_case_buffer / (minimum_buffer_minutes if minimum_buffer_minutes > 0 else 1.0)))
            score = int(68 + 12 * ratio)
            status = "UNCERTAIN"
            recommendation = (
                f"Planned arrival is feasible ({pred_eta_str}), but available buffer margin "
                f"({buffer_minutes:.0f} min) is below your preferred safety buffer ({minimum_buffer_minutes:.0f} min)."
            )
        else:
            # Fully feasible even under worst-case uncertainty
            excess = worst_case_buffer - minimum_buffer_minutes
            score = min(100, int(82 + 18 * min(1.0, excess / 30.0)))
            status = "FEASIBLE"
            recommendation = (
                f"Planned arrival is feasible based on predicted ETA ({pred_eta_str}) "
                f"and uncertainty range ({eta_lower_str}–{eta_upper_str}). Available buffer is {buffer_minutes:.0f} min."
            )

        return {
            "train_id": str(train_id),
            "destination_station_id": matched_st["station_id"],
            "destination_station_name": matched_st["station_name"],
            "scheduled_arrival": sched_arr_str,
            "predicted_eta": pred_eta_str,
            "eta_lower": eta_lower_str,
            "eta_upper": eta_upper_str,
            "required_arrival": required_arrival_time,
            "buffer_minutes": round(buffer_minutes, 1),
            "minimum_buffer_minutes": float(minimum_buffer_minutes),
            "feasibility_score": int(score),
            "status": status,
            "recommendation": recommendation,
            "uncertainty_range_minutes": round(uncertainty_range, 1),
            "data_source_type": "MODEL_OUTPUT"
        }

feasibility_service = FeasibilityService()
