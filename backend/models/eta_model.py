"""
backend/models/eta_model.py
Wraps the trained XGBoost model and empirical uncertainty metrics.
"""

import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_FILE = ARTIFACTS_DIR / "xgb_eta_model.json"
METRICS_FILE = ARTIFACTS_DIR / "model_metrics.json"

class ETAPredictor:
    def __init__(self):
        self.model = None
        self.metrics = {}
        self.feature_cols = [
            "previous_delay_minutes",
            "speed_kmph",
            "dwell_time_minutes",
            "distance_to_next_station_km",
            "day_of_week",
            "hour",
            "section_congestion",
            "historical_recovery_minutes",
            "train_interaction_density",
            "scheduled_travel_time_minutes"
        ]
        self.load_model()
        
    def load_model(self):
        if MODEL_FILE.exists():
            try:
                self.model = xgb.XGBRegressor()
                self.model.load_model(str(MODEL_FILE))
                print(f"[OK] XGBoost model loaded from {MODEL_FILE}")
            except Exception as e:
                print(f"[FAIL] Error loading XGBoost model: {e}")
                self.model = None
        else:
            print(f"[WARN] Model file not found at {MODEL_FILE}. Will use physics heuristic fallback.")
            self.model = None
            
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
                print(f"[OK] Model metrics loaded. Test MAE={self.metrics.get('mae')} min")
            except Exception as e:
                print(f"[WARN] Failed to load metrics: {e}")
                self.metrics = self._default_metrics()
        else:
            self.metrics = self._default_metrics()

    def _default_metrics(self):
        return {
            "algorithm": "XGBRegressor",
            "mae": 2.67,
            "rmse": 5.35,
            "q05_residual": -5.19,
            "q95_residual": 5.69,
            "data_source_type": "SYNTHETIC_CALIBRATED",
            "uncertainty_method": "Empirical residual quantiles (Q05, Q95) on held-out temporal validation set"
        }

    def predict_next_delay(self, features: dict) -> float:
        """Predicts the next station arrival delay in minutes."""
        if self.model is not None:
            # Build DataFrame matching feature ordering
            row_data = {col: [features.get(col, 0.0)] for col in self.feature_cols}
            df_in = pd.DataFrame(row_data)
            pred = float(self.model.predict(df_in)[0])
            return max(0.0, round(pred, 1))
        else:
            # Fallback deterministic physics-based approximation
            curr_delay = features.get("previous_delay_minutes", 0.0)
            congestion = features.get("section_congestion", 0.3)
            slack = features.get("historical_recovery_minutes", 2.0)
            
            delta = (congestion * 6.0) - (slack * 0.5)
            next_delay = max(0.0, curr_delay + delta)
            return round(next_delay, 1)

    def get_uncertainty_bounds(self, predicted_delay: float) -> tuple:
        """
        Calculates empirical lower and upper uncertainty bounds using held-out residuals.
        Residual = y_true - y_pred
        y_true = y_pred + residual
        Lower bound = predicted_delay + Q05 (Q05 is negative)
        Upper bound = predicted_delay + Q95 (Q95 is positive)
        """
        q05 = self.metrics.get("q05_residual", -5.19)
        q95 = self.metrics.get("q95_residual", 5.69)
        
        lower = max(0.0, round(predicted_delay + q05, 1))
        upper = max(lower, round(predicted_delay + q95, 1))
        return lower, upper

# Global singleton instance
predictor = ETAPredictor()
