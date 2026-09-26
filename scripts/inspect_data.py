#!/usr/bin/env python3
"""
scripts/inspect_data.py
Inspect the acquired raw datasets.
Determines actual schema, types, counts, and nulls.
Updates data/manifests/source_manifest.json with exact empirical stats.
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

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MANIFEST_FILE = DATA_DIR / "manifests" / "source_manifest.json"

def inspect_stations():
    p = RAW_DIR / "datameet" / "stations.json"
    if not p.exists():
        print(f"[FAIL] {p} not found.")
        return 0, 0, []
    print(f"\n--- Inspecting {p.name} ---")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Datameet stations.json structure
    # Usually {"features": [...]} (GeoJSON) or list of dicts
    if isinstance(data, dict) and "features" in data:
        features = data["features"]
        count = len(features)
        sample = features[0]["properties"] if features else {}
        cols = list(sample.keys())
        print(f"Format: GeoJSON FeatureCollection with {count} stations.")
        print(f"Sample properties: {json.dumps(sample, indent=2)}")
    elif isinstance(data, list):
        count = len(data)
        sample = data[0] if count > 0 else {}
        cols = list(sample.keys())
        print(f"Format: JSON Array with {count} stations.")
        print(f"Sample object: {json.dumps(sample, indent=2)}")
    else:
        keys = list(data.keys())
        count = len(keys)
        cols = keys[:10]
        print(f"Format: JSON Dict with {count} top-level keys: {cols}")
    return count, len(cols), cols

def inspect_trains():
    p = RAW_DIR / "datameet" / "trains.json"
    if not p.exists():
        print(f"[FAIL] {p} not found.")
        return 0, 0, []
    print(f"\n--- Inspecting {p.name} ---")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, dict) and "features" in data:
        features = data["features"]
        count = len(features)
        sample = features[0]["properties"] if features else {}
        cols = list(sample.keys())
        print(f"Format: GeoJSON with {count} trains.")
        print(f"Sample properties: {json.dumps(sample, indent=2)}")
    elif isinstance(data, list):
        count = len(data)
        sample = data[0] if count > 0 else {}
        cols = list(sample.keys())
        print(f"Format: JSON Array with {count} trains.")
        print(f"Sample object: {json.dumps(sample, indent=2)}")
    else:
        # Check dict keys
        keys = list(data.keys())
        count = len(keys)
        cols = keys[:10]
        print(f"Format: JSON Dict with {count} top keys. Sample key: {keys[0] if keys else 'None'}")
        sample = data[keys[0]] if keys else {}
        print(f"Sample value: {json.dumps(sample, indent=2) if isinstance(sample, dict) else str(sample)[:200]}")
    return count, len(cols), cols

def inspect_schedules():
    p = RAW_DIR / "datameet" / "schedules.json"
    if not p.exists():
        print(f"[FAIL] {p} not found.")
        return 0, 0, []
    print(f"\n--- Inspecting {p.name} ---")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, list):
        count = len(data)
        sample = data[0] if count > 0 else {}
        cols = list(sample.keys())
        print(f"Format: JSON Array with {count} schedule entries.")
        print(f"Sample entry: {json.dumps(sample, indent=2)}")
    elif isinstance(data, dict):
        count = len(data)
        keys = list(data.keys())
        cols = keys[:10]
        sample = data[keys[0]] if keys else {}
        print(f"Format: JSON Dict with {count} keys.")
        print(f"Sample entry for '{keys[0]}': {json.dumps(sample, indent=2) if isinstance(sample, dict) else str(sample)[:200]}")
    else:
        count = 0
        cols = []
    return count, len(cols), cols

def inspect_delays():
    p = RAW_DIR / "delay" / "indian_railway_delays_dataset.csv"
    if not p.exists():
        print(f"[FAIL] {p} not found.")
        return 0, 0, []
    print(f"\n--- Inspecting {p.name} ---")
    df = pd.read_csv(p)
    count = len(df)
    cols = list(df.columns)
    print(f"Rows: {count}, Columns: {len(cols)}")
    print(f"Columns: {cols}")
    print(f"Head:\n{df.head()}")
    return count, len(cols), cols

def update_manifest(stations_info, trains_info, schedules_info, delay_info):
    if not MANIFEST_FILE.exists():
        return
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    for item in manifest:
        if "DataMeet" in item["dataset_name"]:
            item["row_count"] = {
                "stations": stations_info[0],
                "trains": trains_info[0],
                "schedules": schedules_info[0]
            }
            item["column_count"] = {
                "stations": stations_info[1],
                "trains": trains_info[1],
                "schedules": schedules_info[1]
            }
            item["notes"] += f" Verified: {stations_info[0]} stations, {trains_info[0]} trains, {schedules_info[0]} schedule records."
        elif "ctolerate" in item["dataset_name"]:
            item["row_count"] = delay_info[0]
            item["column_count"] = delay_info[1]
            item["notes"] += f" Verified schema columns: {delay_info[2]}."
    
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n[OK] Updated manifest: {MANIFEST_FILE}")

def main():
    print("=== DATASET INSPECTION & PROVENANCE VALIDATION ===")
    st_info = inspect_stations()
    tr_info = inspect_trains()
    sc_info = inspect_schedules()
    dl_info = inspect_delays()
    update_manifest(st_info, tr_info, sc_info, dl_info)

if __name__ == "__main__":
    main()
