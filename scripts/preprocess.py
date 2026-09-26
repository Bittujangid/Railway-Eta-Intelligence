#!/usr/bin/env python3
"""
scripts/preprocess.py
Processes raw railway datasets into normalized relational tables:
1. railway_stations
2. train_master
3. train_schedule
4. historical_delay_data
5. derived_features

Stores outputs in:
- data/processed/*.csv
- backend/data/railway.db (SQLite database)
"""

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import json
import sqlite3
import math
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_DIR = BASE_DIR / "backend" / "data"
DB_PATH = DB_DIR / "railway.db"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate Great Circle distance between two points in km."""
    if any(v is None or math.isnan(v) for v in [lat1, lon1, lat2, lon2]):
        return 0.0
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)

def parse_time_minutes(time_str):
    """Parse HH:MM:SS or HH:MM into minutes from midnight."""
    if not time_str or time_str == "None":
        return None
    try:
        parts = [int(p) for p in time_str.split(":")]
        return parts[0] * 60 + parts[1]
    except Exception:
        return None

def process_stations():
    print("[1/5] Processing railway_stations...")
    stations_path = RAW_DIR / "datameet" / "stations.json"
    with open(stations_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    records = []
    features = data.get("features", [])
    for feat in features:
        props = feat.get("properties", {}) or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates", [None, None]) if isinstance(geom, dict) else [None, None]
        lon = coords[0] if coords and len(coords) > 0 else None
        lat = coords[1] if coords and len(coords) > 1 else None
        
        station_id = str(props.get("code") or "").strip().upper()
        if not station_id:
            continue
        
        records.append({
            "station_id": station_id,
            "station_name": str(props.get("name") or "").strip(),
            "zone": str(props.get("zone") or "").strip(),
            "state": str(props.get("state") or "").strip(),
            "latitude": round(lat, 6) if lat is not None else None,
            "longitude": round(lon, 6) if lon is not None else None,
            "source_type": "PUBLIC_COMMUNITY"
        })
    
    df_stations = pd.DataFrame(records).drop_duplicates(subset=["station_id"])
    csv_path = PROCESSED_DIR / "railway_stations.csv"
    df_stations.to_csv(csv_path, index=False)
    print(f"  Processed {len(df_stations)} stations -> {csv_path.name}")
    return df_stations

def process_trains():
    print("[2/5] Processing train_master...")
    trains_path = RAW_DIR / "datameet" / "trains.json"
    with open(trains_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = []
    features = data.get("features", [])
    for feat in features:
        props = feat.get("properties", {}) or {}
        number = str(props.get("number") or "").strip()
        if not number:
            continue
            
        records.append({
            "train_id": number,
            "train_name": str(props.get("name") or "").strip(),
            "train_type": str(props.get("type") or "").strip(),
            "source_station_id": str(props.get("from_station_code") or "").strip().upper(),
            "source_station_name": str(props.get("from_station_name") or "").strip(),
            "destination_station_id": str(props.get("to_station_code") or "").strip().upper(),
            "destination_station_name": str(props.get("to_station_name") or "").strip(),
            "distance_km": props.get("distance", 0) or 0,
            "duration_hours": round((props.get("duration_h") or 0) + (props.get("duration_m") or 0) / 60.0, 2),
            "source_type": "PUBLIC_COMMUNITY"
        })
        
    df_trains = pd.DataFrame(records).drop_duplicates(subset=["train_id"])
    csv_path = PROCESSED_DIR / "train_master.csv"
    df_trains.to_csv(csv_path, index=False)
    print(f"  Processed {len(df_trains)} trains -> {csv_path.name}")
    return df_trains

def process_schedules(df_stations, df_trains):
    print("[3/5] Processing train_schedule & deriving spatial distances...")
    schedules_path = RAW_DIR / "datameet" / "schedules.json"
    with open(schedules_path, "r", encoding="utf-8") as f:
        schedules = json.load(f)

    # Build station lookup map
    st_dict = df_stations.set_index("station_id")[["latitude", "longitude", "station_name", "zone", "state"]].to_dict(orient="index")

    # Group schedules by train_number
    by_train = {}
    for entry in schedules:
        t_num = str(entry.get("train_number", "")).strip()
        if not t_num:
            continue
        if t_num not in by_train:
            by_train[t_num] = []
        by_train[t_num].append(entry)

    # We will process schedules for popular coaching corridors
    # Ensure flagship trains (12951, 12952, 12002, 12004, 12301, 12302, 12953, 12954, etc.)
    # and all trains in trains.json are processed
    valid_train_ids = set(df_trains["train_id"].unique())
    print(f"  Total trains in schedules: {len(by_train)}. Filtering and sorting route sequences...")

    all_schedules = []
    for t_num, entries in by_train.items():
        if t_num not in valid_train_ids and len(by_train) > 5000:
            continue
        
        # Sort sequentially by schedule 'id'
        entries.sort(key=lambda x: x.get("id", 0))
        
        cum_dist = 0.0
        n = len(entries)
        for seq_idx, e in enumerate(entries):
            st_code = str(e.get("station_code", "")).strip().upper()
            st_info = st_dict.get(st_code, {})
            lat = st_info.get("latitude")
            lon = st_info.get("longitude")
            st_name = e.get("station_name", "") or st_info.get("station_name", st_code)

            # Distance to next station
            next_dist = 0.0
            if seq_idx < n - 1:
                next_code = str(entries[seq_idx + 1].get("station_code", "")).strip().upper()
                next_info = st_dict.get(next_code, {})
                next_lat = next_info.get("latitude")
                next_lon = next_info.get("longitude")
                if lat is not None and next_lat is not None:
                    next_dist = haversine_km(lat, lon, next_lat, next_lon)
            
            all_schedules.append({
                "train_id": t_num,
                "train_name": e.get("train_name", ""),
                "station_id": st_code,
                "station_name": st_name,
                "station_sequence": seq_idx + 1,
                "scheduled_arrival": e.get("arrival") if e.get("arrival") != "None" else None,
                "scheduled_departure": e.get("departure") if e.get("departure") != "None" else None,
                "day": e.get("day", 1),
                "distance_from_origin_km": round(cum_dist, 2),
                "distance_to_next_station_km": round(next_dist, 2),
                "latitude": lat,
                "longitude": lon,
                "source_type": "DERIVED" if next_dist > 0 else "PUBLIC_COMMUNITY"
            })
            cum_dist += next_dist

    df_schedules = pd.DataFrame(all_schedules)
    csv_path = PROCESSED_DIR / "train_schedule.csv"
    df_schedules.to_csv(csv_path, index=False)
    print(f"  Processed {len(df_schedules)} schedule rows across {len(by_train)} trains -> {csv_path.name}")
    return df_schedules

def process_historical_delays():
    print("[4/5] Processing historical_delay_data (Authentic Public Records)...")
    delay_path = RAW_DIR / "delay" / "indian_railway_delays_dataset.csv"
    if delay_path.exists():
        df_delays = pd.read_csv(delay_path)
        df_delays["source_type"] = "PUBLIC_COMMUNITY"
        csv_path = PROCESSED_DIR / "historical_delay_data.csv"
        df_delays.to_csv(csv_path, index=False)
        print(f"  Processed {len(df_delays)} authentic delay summary rows -> {csv_path.name}")
        return df_delays
    else:
        print("  Notice: Public delay records not found. Recording empty schema table.")
        cols = ["train_id", "train_name", "date", "station_id", "station_name", "scheduled_arrival", "actual_arrival", "delay_minutes", "source_type"]
        df_delays = pd.DataFrame(columns=cols)
        df_delays.to_csv(PROCESSED_DIR / "historical_delay_data.csv", index=False)
        return df_delays

def process_derived_features(df_schedules):
    print("[5/5] Deriving railway features (dwell, travel time, headway & speed baseline)...")
    
    # Select key coaching trains for featured analytics
    # E.g. trains with >= 5 stations
    train_lens = df_schedules.groupby("train_id")["station_sequence"].count()
    valid_trains = train_lens[train_lens >= 5].index
    sub_sched = df_schedules[df_schedules["train_id"].isin(valid_trains)].copy()

    derived_rows = []
    grouped = sub_sched.groupby("train_id")
    
    for train_id, group in grouped:
        group = group.sort_values("station_sequence").reset_index(drop=True)
        n = len(group)
        for i in range(n):
            row = group.iloc[i]
            arr_str = row["scheduled_arrival"]
            dep_str = row["scheduled_departure"]
            day = row["day"]
            
            arr_m = parse_time_minutes(arr_str)
            dep_m = parse_time_minutes(dep_str)
            
            # Dwell time
            if arr_m is not None and dep_m is not None:
                dwell = dep_m - arr_m
                if dwell < 0:
                    dwell += 24 * 60
            else:
                dwell = 0
            
            # Scheduled travel time to next station
            sched_travel_m = 0
            avg_speed = 0.0
            if i < n - 1:
                next_row = group.iloc[i+1]
                next_arr_str = next_row["scheduled_arrival"]
                next_day = next_row["day"]
                next_arr_m = parse_time_minutes(next_arr_str)
                dep_cur = dep_m if dep_m is not None else arr_m
                if dep_cur is not None and next_arr_m is not None:
                    delta_day = next_day - day
                    sched_travel_m = (delta_day * 24 * 60 + next_arr_m) - dep_cur
                    if sched_travel_m < 0:
                        sched_travel_m += 24 * 60
                    if sched_travel_m > 0 and row["distance_to_next_station_km"] > 0:
                        avg_speed = round(row["distance_to_next_station_km"] / (sched_travel_m / 60.0), 1)

            # Hour of the day
            ref_m = dep_m if dep_m is not None else (arr_m if arr_m is not None else 720)
            hour = (ref_m // 60) % 24
            
            derived_rows.append({
                "train_id": train_id,
                "station_id": row["station_id"],
                "station_sequence": row["station_sequence"],
                "dwell_time_minutes": dwell,
                "scheduled_travel_time_minutes": sched_travel_m,
                "distance_to_next_station_km": row["distance_to_next_station_km"],
                "scheduled_speed_kmph": avg_speed,
                "hour": hour,
                "day_of_week": (day % 7) + 1,
                "source_type": "DERIVED"
            })
            
    df_derived = pd.DataFrame(derived_rows)
    csv_path = PROCESSED_DIR / "derived_features.csv"
    df_derived.to_csv(csv_path, index=False)
    print(f"  Generated {len(df_derived)} derived feature records -> {csv_path.name}")
    return df_derived

def store_in_sqlite(df_stations, df_trains, df_schedules, df_delays, df_derived):
    print(f"\nWriting processed tables to SQLite: {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    
    df_stations.to_sql("railway_stations", conn, if_exists="replace", index=False)
    df_trains.to_sql("train_master", conn, if_exists="replace", index=False)
    # Store top 1000 trains schedules into SQLite for fast querying, full in CSV
    df_schedules.to_sql("train_schedule", conn, if_exists="replace", index=False)
    df_delays.to_sql("historical_delay_data", conn, if_exists="replace", index=False)
    df_derived.to_sql("derived_features", conn, if_exists="replace", index=False)
    
    # Create indices
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stations_id ON railway_stations(station_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trains_id ON train_master(train_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_train ON train_schedule(train_id, station_sequence);")
    conn.commit()
    conn.close()
    print("  [OK] SQLite database initialized with indexed tables.")

def main():
    print("=== DATA PREPROCESSING & RELATIONAL MAPPING ===")
    df_stations = process_stations()
    df_trains = process_trains()
    df_schedules = process_schedules(df_stations, df_trains)
    df_delays = process_historical_delays()
    df_derived = process_derived_features(df_schedules)
    store_in_sqlite(df_stations, df_trains, df_schedules, df_delays, df_derived)
    print("\nPre-processing complete.")

if __name__ == "__main__":
    main()
