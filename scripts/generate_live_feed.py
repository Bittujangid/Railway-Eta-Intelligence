#!/usr/bin/env python3
"""
scripts/generate_live_feed.py
Generates the baseline simulated live feed for the SIH26028 prototype.

Adheres strictly to Data Honesty:
- feed_type = 'SIMULATED_LIVE'
- data_source_type = 'SYNTHETIC_DEMO'
- Follows real railway route coordinates, stations, and sequence.
- Distinguishes STOPPED_STATION (speed=0) vs IN_TRANSIT (speed>0).
- Models scenarios: NORMAL, CONGESTION, SEVERE_DELAY.
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
SIMULATED_DIR = DATA_DIR / "simulated"
SIMULATED_DIR.mkdir(parents=True, exist_ok=True)

LIVE_FEED_PATH = SIMULATED_DIR / "simulated_live_feed.csv"

def generate_live_feed():
    print("=== GENERATING BASELINE SIMULATED LIVE FEED ===")
    schedules_file = PROCESSED_DIR / "train_schedule.csv"
    trains_file = PROCESSED_DIR / "train_master.csv"
    
    if not (schedules_file.exists() and trains_file.exists()):
        print("[FAIL] Processed schedule or train master missing.")
        sys.exit(1)
        
    df_schedules = pd.read_csv(schedules_file)
    df_trains = pd.read_csv(trains_file)
    
    # Primary demo train: 12951 (Mumbai Central - New Delhi Rajdhani)
    # Secondary demo trains: 12004 (New Delhi - Lucknow Shatabdi), 12002 (New Delhi - Bhopal Shatabdi)
    demo_train_ids = ["12951", "12004", "12002"]
    
    feed_records = []
    now_iso = datetime.now(timezone.utc).isoformat()
    
    for train_id in demo_train_ids:
        t_sched = df_schedules[df_schedules["train_id"].astype(str) == str(train_id)].sort_values("station_sequence").reset_index(drop=True)
        if len(t_sched) < 6:
            continue
            
        t_name = t_sched.iloc[0]["train_name"]
        
        # Position train at a realistic mid-journey station
        # For 12951: at KOTA (sequence 143)
        if str(train_id) == "12951":
            cur_idx = 142  # 0-indexed, station_sequence 143 (KOTA)
            cur_st = t_sched.iloc[cur_idx]
            next_st = t_sched.iloc[cur_idx + 1]
        else:
            cur_idx = int(len(t_sched) * 0.45)
            cur_st = t_sched.iloc[cur_idx]
            next_st = t_sched.iloc[cur_idx + 1]
            
        # Initial delays per scenario:
        # NORMAL: 18 min initial delay, low congestion (recovery expected)
        # CONGESTION: 22 min initial delay, high section congestion (delay increase)
        # SEVERE_DELAY: 45 min initial delay, saturated corridor (heavy delay increase)
        scenarios = [
            {
                "name": "NORMAL",
                "delay": 18.0,
                "status": "STOPPED_STATION",
                "speed": 0.0,
                "congestion": 0.22,
                "condition": "CLEAR_TRACK"
            },
            {
                "name": "CONGESTION",
                "delay": 22.0,
                "status": "IN_TRANSIT",
                "speed": 52.0,
                "congestion": 0.78,
                "condition": "HEAVY_FREIGHT_INTERACTION"
            },
            {
                "name": "SEVERE_DELAY",
                "delay": 48.0,
                "status": "STOPPED_STATION",
                "speed": 0.0,
                "congestion": 0.95,
                "condition": "SIGNAL_FAILURE_SECTION_BLOCK"
            }
        ]
        
        for sc in scenarios:
            feed_records.append({
                "timestamp": now_iso,
                "train_id": str(train_id),
                "train_name": t_name,
                "current_station_id": cur_st["station_id"],
                "current_station_name": cur_st["station_name"],
                "current_station_sequence": int(cur_st["station_sequence"]),
                "latitude": float(cur_st["latitude"]) if pd.notnull(cur_st["latitude"]) else 25.18,
                "longitude": float(cur_st["longitude"]) if pd.notnull(cur_st["longitude"]) else 75.83,
                "delay_minutes": float(sc["delay"]),
                "speed_kmph": float(sc["speed"]),
                "current_status": sc["status"],
                "next_station_id": next_st["station_id"],
                "next_station_name": next_st["station_name"],
                "distance_to_next_station_km": float(cur_st["distance_to_next_station_km"]),
                "congestion_level": float(sc["congestion"]),
                "section_condition": sc["condition"],
                "scenario": sc["name"],
                "feed_type": "SIMULATED_LIVE",
                "data_source_type": "SYNTHETIC_DEMO"
            })
            
    df_feed = pd.DataFrame(feed_records)
    df_feed.to_csv(LIVE_FEED_PATH, index=False)
    print(f"Generated {len(df_feed)} baseline simulated live feed records.")
    print(f"Saved to: {LIVE_FEED_PATH}")

if __name__ == "__main__":
    generate_live_feed()
