#!/usr/bin/env python3
"""
scripts/train_models.py
Trains the dynamic train delay forecasting model using XGBoost Regressor.

Strict Data Honesty & ML Principles:
1. Temporal Train/Test Split:
   - Early dates (2026-08-01 to 2026-08-22) -> Training Set
   - Later dates (2026-08-23 to 2026-08-30) -> Held-out Test Set
   - Zero random data shuffling across time.
2. Target: target_delay_minutes (arrival delay at upcoming station)
3. Zero Temporal Leakage: All candidate features represent state at prediction time.
4. ETA Uncertainty Estimation:
   - Evaluates test set residuals: residual = y_true - y_pred
   - Computes empirical quantiles Q05 and Q95 on held-out test residuals.
   - Calculates empirical test MAE and RMSE.
5. Saves model artifact and metrics to backend/artifacts/.
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import json
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CORPUS_PATH = DATA_DIR / "synthetic" / "calibrated_training_corpus.csv"
ARTIFACTS_DIR = BASE_DIR / "backend" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = ARTIFACTS_DIR / "xgb_eta_model.json"
METRICS_FILE = ARTIFACTS_DIR / "model_metrics.json"

FEATURE_COLS = [
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

TARGET_COL = "target_delay_minutes"

def train():
    print("=== TRAINING XGBOOST DYNAMIC ETA FORECAST MODEL ===")
    if not CORPUS_PATH.exists():
        print(f"[FAIL] Training corpus not found: {CORPUS_PATH}")
        sys.exit(1)
        
    print(f"Loading corpus from {CORPUS_PATH}...")
    df = pd.read_csv(CORPUS_PATH)
    print(f"Loaded {len(df)} records.")
    
    # 1. Temporal Train/Test Split
    split_date = "2026-08-22"
    train_mask = df["date"] <= split_date
    test_mask = df["date"] > split_date
    
    df_train = df[train_mask].copy()
    df_test = df[test_mask].copy()
    
    train_dates = (df_train["date"].min(), df_train["date"].max())
    test_dates = (df_test["date"].min(), df_test["date"].max())
    
    print(f"Temporal Split Date: {split_date}")
    print(f"  Training Set: {len(df_train)} rows ({train_dates[0]} to {train_dates[1]})")
    print(f"  Test Set:     {len(df_test)} rows ({test_dates[0]} to {test_dates[1]})")
    
    X_train = df_train[FEATURE_COLS]
    y_train = df_train[TARGET_COL]
    
    X_test = df_test[FEATURE_COLS]
    y_test = df_test[TARGET_COL]
    
    # 2. Configure XGBRegressor
    print("\nTraining XGBRegressor...")
    regressor = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        random_state=42,
        n_jobs=-1
    )
    
    regressor.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=50
    )
    
    # 3. Held-out Test Set Evaluation
    print("\nEvaluating on Held-Out Temporal Test Set...")
    y_pred = regressor.predict(X_test)
    
    # Clip delay predictions to physically valid non-negative values
    y_pred_clipped = np.clip(y_pred, 0.0, None)
    
    mae = float(mean_absolute_error(y_test, y_pred_clipped))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_clipped)))
    
    # 4. Residual Distribution & Empirical Quantiles (Section 14)
    # residual = y_true - y_pred
    # Positive residual means train was delayed MORE than predicted.
    # Negative residual means train was delayed LESS than predicted.
    residuals = y_test - y_pred_clipped
    q05_residual = float(np.percentile(residuals, 5))
    q95_residual = float(np.percentile(residuals, 95))
    
    print("--- Model Performance Metrics ---")
    print(f"  Validation MAE:  {mae:.2f} minutes")
    print(f"  Validation RMSE: {rmse:.2f} minutes")
    print(f"  Residual Q05:    {q05_residual:.2f} minutes")
    print(f"  Residual Q95:    {q95_residual:.2f} minutes")
    
    # Feature Importances
    importances = {feat: round(float(imp), 4) for feat, imp in zip(FEATURE_COLS, regressor.feature_importances_)}
    sorted_importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
    print("\nFeature Importances:")
    for feat, imp in sorted_importances.items():
        print(f"  {feat:30s}: {imp:.4f}")
        
    # 5. Save Model and Metrics
    regressor.save_model(str(MODEL_FILE))
    print(f"\nModel saved: {MODEL_FILE}")
    
    metrics_data = {
        "algorithm": "XGBRegressor",
        "features": FEATURE_COLS,
        "target": TARGET_COL,
        "train_rows": len(df_train),
        "test_rows": len(df_test),
        "train_date_range": f"{train_dates[0]} to {train_dates[1]}",
        "test_date_range": f"{test_dates[0]} to {test_dates[1]}",
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "q05_residual": round(q05_residual, 2),
        "q95_residual": round(q95_residual, 2),
        "data_source_type": "SYNTHETIC_CALIBRATED",
        "feature_importances": sorted_importances,
        "uncertainty_method": "Empirical residual quantiles (Q05, Q95) on held-out temporal validation set"
    }
    
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"Metrics saved: {METRICS_FILE}")
    print("\n[OK] Model training complete.")

if __name__ == "__main__":
    train()
