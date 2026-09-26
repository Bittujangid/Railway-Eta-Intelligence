#!/usr/bin/env python3
"""
scripts/generate_synthetic_training.py
Generates a physics-calibrated synthetic training corpus based strictly on the
real Indian Railways network topology, station sequences, distances, and timetables.

Data Honesty:
- Every record explicitly contains: data_source_type = 'SYNTHETIC_CALIBRATED'
- Saved separately in data/synthetic/calibrated_training_corpus.csv
- Prevents temporal leakage: only features observable at observation time are included.
- Complies with speed feature rule:
    STOPPED_STATION -> speed_kmph = 0
    IN_TRANSIT       -> speed_kmph > 0
- Uses a temporal date range (e.g., 2026-08-01 to 2026-08-30) for chronological train/test split.
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import random
import math
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# Set deterministic seed for reproducibility
np.random.seed(42)
random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)

CORPUS_PATH = SYNTHETIC_DIR / "calibrated_training_corpus.csv"

def generate_calibrated_corpus():
    print("=== GENERATING PHYSICS-CALIBRATED SYNTHETIC TRAINING CORPUS ===")
    
    # Load processed schedules and trains
    schedules_file = PROCESSED_DIR / "train_schedule.csv"
    trains_file = PROCESSED_DIR / "train_master.csv"
    derived_file = PROCESSED_DIR / "derived_features.csv"
    
    if not (schedules_file.exists() and trains_file.exists() and derived_file.exists()):
        print("[FAIL] Processed datasets missing. Run preprocess.py first.")
        sys.exit(1)
        
    print("Loading processed timetable and topology data...")
    df_schedules = pd.read_csv(schedules_file)
    df_trains = pd.read_csv(trains_file)
    df_derived = pd.read_csv(derived_file)
    
    # Select candidate trains: prominent coaching trains with 8 to 50 stations
    st_counts = df_schedules.groupby("train_id")["station_sequence"].count()
    candidate_train_ids = st_counts[(st_counts >= 8) & (st_counts <= 50)].index.tolist()
    
    # Ensure flagship trains like 12951, 12952, 12002, 12004 are included if available
    flagships = ["12951", "12952", "12002", "12004", "12953", "12954", "12301", "12302"]
    priority_ids = [t for t in flagships if t in st_counts.index]
    
    # Sample 100 representative coaching trains for diverse network training
    sampled_ids = list(set(priority_ids + random.sample(candidate_train_ids, min(100, len(candidate_train_ids)))))
    print(f"Selected {len(sampled_ids)} real trains across diverse railway routes.")
    
    sub_sched = df_schedules[df_schedules["train_id"].isin(sampled_ids)].copy()
    sub_sched.sort_values(by=["train_id", "station_sequence"], inplace=True)
    
    # Join with derived features for dwell, scheduled travel time, etc.
    sub_derived = df_derived.set_index(["train_id", "station_id", "station_sequence"])
    
    # Generate temporal dates: 30 days (2026-08-01 to 2026-08-30)
    # Days 1-22 will be Train, Days 23-30 will be Test
    start_date = datetime.date(2026, 8, 1)
    date_list = [start_date + datetime.timedelta(days=d) for d in range(30)]
    print(f"Simulating operational trips across {len(date_list)} calendar days (Temporal span)...")
    
    corpus_records = []
    
    train_groups = sub_sched.groupby("train_id")
    
    total_trips = len(sampled_ids) * len(date_list)
    processed_trips = 0
    
    for date in date_list:
        day_of_week = date.isoweekday()  # 1=Monday, 7=Sunday
        is_weekend = day_of_week in [6, 7]
        
        for train_id, group in train_groups:
            processed_trips += 1
            stations_list = group.to_dict(orient="records")
            num_stations = len(stations_list)
            if num_stations < 4:
                continue
                
            # Initial origin delay: mostly 0 to 10 mins, occasionally delayed up to 35 mins
            if random.random() < 0.65:
                curr_delay = max(0.0, round(np.random.exponential(scale=4.0), 1))
            elif random.random() < 0.85:
                curr_delay = round(random.uniform(10.0, 30.0), 1)
            else:
                curr_delay = round(random.uniform(30.0, 75.0), 1)
                
            # Simulate through the route
            for seq_idx in range(num_stations - 1):
                cur_st = stations_list[seq_idx]
                next_st = stations_list[seq_idx + 1]
                
                dist_next = cur_st.get("distance_to_next_station_km", 0.0)
                if dist_next <= 0:
                    dist_next = 15.0  # nominal section distance
                    
                # Lookup derived features
                train_id_key = str(train_id)
                st_code_key = cur_st.get("station_id")
                seq_key = cur_st.get("station_sequence")
                
                derived_info = {}
                if (train_id_key, st_code_key, seq_key) in sub_derived.index:
                    derived_info = sub_derived.loc[(train_id_key, st_code_key, seq_key)].to_dict()
                    
                sched_dwell = derived_info.get("dwell_time_minutes", 2.0)
                sched_travel_m = derived_info.get("scheduled_travel_time_minutes", 0.0)
                if sched_travel_m <= 0:
                    # Estimate based on nominal speed 70 km/h
                    sched_travel_m = max(5.0, round((dist_next / 70.0) * 60.0, 1))
                    
                hour = derived_info.get("hour", 12)
                
                # Section Congestion: higher during peak hours (08-11, 17-21) and weekends
                base_congestion = 0.25
                if hour in [8, 9, 10, 17, 18, 19, 20]:
                    base_congestion += 0.35
                if is_weekend:
                    base_congestion += 0.15
                section_congestion = round(min(1.0, max(0.05, base_congestion + np.random.normal(0, 0.12))), 3)
                
                # Train Interaction Density: heuristic proxy (0 to 5 nearby trains)
                interaction_density = int(min(5, max(0, round(section_congestion * 4 + np.random.poisson(lam=0.8)))))
                
                # Timetable Slack / Historical Recovery potential
                # Indian Railways timetables embed 5-15% slack in running times
                timetable_slack = round(max(0.0, sched_travel_m * 0.08 + random.uniform(0.5, 3.0)), 1)
                
                # Distinguish TRAIN_STATUS at prediction time:
                # 50% chance train is observed STOPPED_STATION, 50% IN_TRANSIT
                obs_status = "STOPPED_STATION" if (random.random() < 0.5) else "IN_TRANSIT"
                
                if obs_status == "STOPPED_STATION":
                    speed_kmph = 0.0
                    # Dwell variation: extra passenger rush or clearance delay
                    dwell_variation = max(-1.0, round(np.random.exponential(scale=1.5) - 0.5, 1))
                    actual_dwell = max(1.0, sched_dwell + dwell_variation)
                    dwell_delay_delta = max(0.0, actual_dwell - sched_dwell)
                    curr_delay = round(curr_delay + dwell_delay_delta, 1)
                else:
                    # IN_TRANSIT: Train is running between stations
                    # Speed is positive, constrained by section congestion
                    max_sec_speed = random.choice([90, 110, 120, 130])
                    actual_sec_speed = max_sec_speed * (1.0 - 0.55 * section_congestion)
                    speed_kmph = round(max(25.0, actual_sec_speed + np.random.normal(0, 5)), 1)
                    
                # Physics of section transit to next station:
                # Travel time depends on section distance, average transit speed, congestion & interactions
                nominal_speed = (dist_next / (sched_travel_m / 60.0)) if sched_travel_m > 0 else 70.0
                effective_speed = nominal_speed * (1.0 - 0.45 * section_congestion - 0.05 * interaction_density)
                effective_speed = max(20.0, min(130.0, effective_speed + np.random.normal(0, 4.0)))
                
                actual_travel_m = round((dist_next / effective_speed) * 60.0, 1)
                travel_delta = actual_travel_m - sched_travel_m
                
                # Delay Recovery Mechanism:
                # If current delay > 5 min, the crew pushes speed within safe limits to recover slack time
                recovery_achieved = 0.0
                if curr_delay > 5.0 and section_congestion < 0.6:
                    recovery_achieved = round(min(curr_delay * 0.4, timetable_slack * (1.0 - section_congestion)), 1)
                    
                # Next station arrival delay
                next_delay = round(max(0.0, curr_delay + travel_delta - recovery_achieved), 1)
                
                # Add sample record with ZERO TEMPORAL LEAKAGE
                corpus_records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "train_id": str(train_id),
                    "train_name": cur_st.get("train_name", ""),
                    "station_id": cur_st.get("station_id"),
                    "station_name": cur_st.get("station_name"),
                    "station_sequence": cur_st.get("station_sequence"),
                    "next_station_id": next_st.get("station_id"),
                    "next_station_name": next_st.get("station_name"),
                    "train_status": obs_status,
                    "previous_delay_minutes": float(curr_delay),
                    "speed_kmph": float(speed_kmph),
                    "dwell_time_minutes": float(sched_dwell),
                    "distance_to_next_station_km": float(dist_next),
                    "day_of_week": int(day_of_week),
                    "hour": int(hour),
                    "section_congestion": float(section_congestion),
                    "historical_recovery_minutes": float(timetable_slack),
                    "train_interaction_density": int(interaction_density),
                    "scheduled_travel_time_minutes": float(sched_travel_m),
                    "data_source_type": "SYNTHETIC_CALIBRATED",
                    "target_delay_minutes": float(next_delay)
                })
                
                # Update curr_delay for the next station simulation
                curr_delay = next_delay

    df_corpus = pd.DataFrame(corpus_records)
    print(f"\nSynthetic training corpus generated: {len(df_corpus)} rows, {len(df_corpus.columns)} columns.")
    print("Sample distribution of Train Status:")
    print(df_corpus["train_status"].value_counts())
    print("\nSpeed verification:")
    stopped_speeds = df_corpus[df_corpus["train_status"] == "STOPPED_STATION"]["speed_kmph"]
    transit_speeds = df_corpus[df_corpus["train_status"] == "IN_TRANSIT"]["speed_kmph"]
    print(f"STOPPED_STATION speeds (min, max): {stopped_speeds.min()}, {stopped_speeds.max()}")
    print(f"IN_TRANSIT speeds (min, max): {transit_speeds.min()}, {transit_speeds.max()}")
    assert (stopped_speeds == 0.0).all(), "Critical error: Stopped train speed must be 0!"
    assert (transit_speeds > 0.0).all(), "Critical error: In-transit train speed must be > 0!"
    
    # Save to CSV
    df_corpus.to_csv(CORPUS_PATH, index=False)
    print(f"[OK] Calibrated training corpus saved to: {CORPUS_PATH}")

if __name__ == "__main__":
    generate_calibrated_corpus()
