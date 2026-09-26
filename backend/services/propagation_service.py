"""
backend/services/propagation_service.py
Assesses train interaction and delay propagation risk using transparent heuristics.
Explicitly labeled: 'Propagation Risk — Prototype Heuristic' (Section 17).
"""

from typing import Dict, Any
from backend.services.live_simulator import live_simulator

class PropagationService:
    def evaluate_propagation_risk(self, train_id: str) -> Dict[str, Any]:
        live_state = live_simulator.get_live_state(train_id)
        if not live_state:
            return {
                "train_id": train_id,
                "current_station": "Unknown",
                "next_station": "Unknown",
                "propagation_risk": "LOW",
                "headway_minutes": 25.0,
                "train_interaction_density": 1,
                "section_congestion": 0.2,
                "downstream_impacted_trains": 0,
                "assessment_label": "Propagation Risk — Prototype Heuristic"
            }

        delay = live_state.get("delay_minutes", 18.0)
        congestion = live_state.get("congestion_level", 0.25)
        scenario = live_state.get("scenario", "NORMAL")

        # Headway calculation (simulated section occupancy buffer)
        if scenario == "NORMAL":
            headway_mins = 24.0
            interaction_density = 1
            impacted = 0
        elif scenario == "CONGESTION":
            headway_mins = 11.0
            interaction_density = 3
            impacted = 2
        else:  # SEVERE_DELAY
            headway_mins = 6.0
            interaction_density = 5
            impacted = 5

        # Heuristic Risk Classification
        if delay >= 40.0 or (delay >= 20.0 and headway_mins <= 10.0):
            risk = "HIGH"
        elif delay >= 15.0 or headway_mins <= 15.0 or congestion >= 0.6:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "train_id": str(train_id),
            "current_station": live_state.get("current_station_name", ""),
            "next_station": live_state.get("next_station_name", ""),
            "propagation_risk": risk,
            "headway_minutes": headway_mins,
            "train_interaction_density": interaction_density,
            "section_congestion": congestion,
            "downstream_impacted_trains": impacted,
            "assessment_label": "Propagation Risk — Prototype Heuristic"
        }

propagation_service = PropagationService()
