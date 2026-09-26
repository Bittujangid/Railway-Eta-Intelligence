"""
backend/services/live_simulator.py
Simulates real-time telemetry feed for coaching trains across operational scenarios.

Strict Physical Rules:
- STOPPED_STATION -> speed_kmph = 0
- IN_TRANSIT       -> speed_kmph > 0
- Position matches real geographic coordinates of the railway route.
- feed_type = 'SIMULATED_LIVE'
- data_source_type = 'SYNTHETIC_DEMO'
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd
from backend.services.data_service import data_service

class LiveSimulationManager:
    def __init__(self):
        self.active_scenario = "NORMAL"
        # Train-specific state overrides
        self.train_states: Dict[str, Dict[str, Any]] = {}
        self.initialize_states()

    def initialize_states(self):
        """Initialize demo train live states from real route timetables."""
        demo_trains = ["12951", "12004", "12002"]
        
        for t_id in demo_trains:
            sched = data_service.get_train_schedule(t_id)
            if not sched:
                continue
                
            # For 12951 (Mumbai-Delhi Rajdhani), position at Kota Jn (sequence 143)
            if t_id == "12951":
                target_seq = 143
            else:
                target_seq = max(2, int(len(sched) * 0.4))
                
            cur_idx = 0
            for idx, s in enumerate(sched):
                if s["station_sequence"] == target_seq:
                    cur_idx = idx
                    break
                    
            cur_st = sched[cur_idx]
            next_st = sched[min(len(sched) - 1, cur_idx + 1)]
            
            self.train_states[t_id] = {
                "train_id": t_id,
                "train_name": cur_st["train_name"],
                "current_station_id": cur_st["station_id"],
                "current_station_name": cur_st["station_name"],
                "current_station_sequence": cur_st["station_sequence"],
                "latitude": cur_st["latitude"] or 25.18,
                "longitude": cur_st["longitude"] or 75.83,
                "next_station_id": next_st["station_id"],
                "next_station_name": next_st["station_name"],
                "distance_to_next_station_km": cur_st["distance_to_next_station_km"],
                "scenario": "NORMAL",
                "delay_minutes": 16.0,
                "speed_kmph": 0.0,
                "current_status": "STOPPED_STATION",
                "congestion_level": 0.22,
                "section_condition": "CLEAR_TRACK"
            }

    def set_scenario(self, scenario: str, train_id: Optional[str] = None) -> Dict[str, Any]:
        """Switch simulation scenario and update live parameters accordingly."""
        valid_scenarios = ["NORMAL", "CONGESTION", "SEVERE_DELAY"]
        if scenario.upper() not in valid_scenarios:
            scenario = "NORMAL"
        else:
            scenario = scenario.upper()
            
        self.active_scenario = scenario
        
        target_ids = [train_id] if train_id and train_id in self.train_states else list(self.train_states.keys())
        
        for tid in target_ids:
            state = self.train_states.get(tid)
            if not state:
                continue
                
            state["scenario"] = scenario
            
            if scenario == "NORMAL":
                state["delay_minutes"] = 16.0
                state["current_status"] = "STOPPED_STATION"
                state["speed_kmph"] = 0.0
                state["congestion_level"] = 0.20
                state["section_condition"] = "CLEAR_TRACK_RECOVERY_FAVOURABLE"
            elif scenario == "CONGESTION":
                state["delay_minutes"] = 24.0
                state["current_status"] = "IN_TRANSIT"
                state["speed_kmph"] = 48.0
                state["congestion_level"] = 0.78
                state["section_condition"] = "HEAVY_FREIGHT_TRAFFIC_RESTRICTED"
            elif scenario == "SEVERE_DELAY":
                state["delay_minutes"] = 52.0
                state["current_status"] = "STOPPED_STATION"
                state["speed_kmph"] = 0.0
                state["congestion_level"] = 0.94
                state["section_condition"] = "SIGNALING_DISRUPTION_SECTION_GRIDLOCK"

        primary_id = train_id or "12951"
        return self.get_live_state(primary_id)

    def get_live_state(self, train_id: str) -> Dict[str, Any]:
        """Returns the current simulated live telemetry."""
        if train_id not in self.train_states:
            # Fallback initialization for any train requested
            sched = data_service.get_train_schedule(train_id)
            if sched:
                mid = max(1, len(sched) // 3)
                cur = sched[mid]
                nxt = sched[min(len(sched) - 1, mid + 1)]
                self.train_states[train_id] = {
                    "train_id": str(train_id),
                    "train_name": cur["train_name"],
                    "current_station_id": cur["station_id"],
                    "current_station_name": cur["station_name"],
                    "current_station_sequence": cur["station_sequence"],
                    "latitude": cur["latitude"] or 20.0,
                    "longitude": cur["longitude"] or 77.0,
                    "next_station_id": nxt["station_id"],
                    "next_station_name": nxt["station_name"],
                    "distance_to_next_station_km": cur["distance_to_next_station_km"],
                    "scenario": self.active_scenario,
                    "delay_minutes": 18.0,
                    "speed_kmph": 0.0,
                    "current_status": "STOPPED_STATION",
                    "congestion_level": 0.25,
                    "section_condition": "CLEAR_TRACK"
                }
            else:
                return {}

        state = self.train_states[train_id].copy()
        
        # Enforce physical rule:
        if state["current_status"] == "STOPPED_STATION":
            state["speed_kmph"] = 0.0
        elif state["current_status"] == "IN_TRANSIT" and state["speed_kmph"] <= 0.0:
            state["speed_kmph"] = 65.0

        state["timestamp"] = datetime.now(timezone.utc).isoformat()
        state["feed_type"] = "SIMULATED_LIVE"
        state["data_source_type"] = "SYNTHETIC_DEMO"
        return state

live_simulator = LiveSimulationManager()
