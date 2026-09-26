"""
backend/models/evolution_model.py
Determines delay evolution (RECOVER / MAINTAIN / INCREASE) and explains contributing factors.
"""

from typing import Dict, Any, List

class DelayEvolutionEngine:
    def __init__(self, recover_threshold: float = -3.0, increase_threshold: float = 3.0):
        self.recover_threshold = recover_threshold
        self.increase_threshold = increase_threshold

    def classify_evolution(self, current_delay: float, predicted_delay: float) -> tuple:
        """
        Classifies delay evolution based on transparent delta thresholds:
        delta = predicted_delay - current_delay
        < -3.0 min -> RECOVER
        -3.0 to +3.0 min -> MAINTAIN
        > +3.0 min -> INCREASE
        """
        delta = round(predicted_delay - current_delay, 1)
        if delta < self.recover_threshold:
            status = "RECOVER"
        elif delta > self.increase_threshold:
            status = "INCREASE"
        else:
            status = "MAINTAIN"
        return status, delta

    def explain_eta_change(self, features: dict, delta_delay: float) -> List[Dict[str, Any]]:
        """
        Explains contributing factors to the ETA change using actual feature magnitudes:
        - Section congestion
        - Historical timetable recovery slack
        - Dwell time variation
        - Train interaction density
        """
        explanations = []
        congestion = features.get("section_congestion", 0.3)
        slack = features.get("historical_recovery_minutes", 2.0)
        dwell = features.get("dwell_time_minutes", 2.0)
        interactions = features.get("train_interaction_density", 0)
        speed = features.get("speed_kmph", 0.0)

        # 1. Congestion impact
        if congestion >= 0.7:
            explanations.append({
                "factor": "High Section Congestion",
                "impact_minutes": round(congestion * 6.5, 1),
                "direction": "+",
                "description": f"Heavy corridor traffic (level {congestion:.2f}) constraining maximum line speed."
            })
        elif congestion <= 0.3:
            explanations.append({
                "factor": "Clear Corridor Track",
                "impact_minutes": round(-1.5, 1),
                "direction": "-",
                "description": "Favorable section capacity allowing sustained track clearance."
            })

        # 2. Historical recovery slack
        if slack > 1.5:
            explanations.append({
                "factor": "Timetable Buffer Slack",
                "impact_minutes": round(-slack * 0.7, 1),
                "direction": "-",
                "description": f"{slack:.1f} min scheduled buffer enables progressive delay absorption."
            })

        # 3. Train interaction
        if interactions >= 2:
            explanations.append({
                "factor": "Platform / Junction Crossing",
                "impact_minutes": round(interactions * 1.2, 1),
                "direction": "+",
                "description": f"{interactions} proximate scheduled trains creating cautionary speed limits."
            })

        # 4. Status / Speed factor
        if speed == 0.0 and dwell > 5.0:
            explanations.append({
                "factor": "Extended Station Dwell",
                "impact_minutes": round(dwell * 0.4, 1),
                "direction": "+",
                "description": "Prolonged passenger boarding and rake clearance at platform."
            })

        return explanations

evolution_engine = DelayEvolutionEngine()
