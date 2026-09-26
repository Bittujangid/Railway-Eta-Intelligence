"""
backend/services/data_service.py
Data layer service accessing processed SQLite database and schedule topology.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "railway.db"

class DataService:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_featured_trains(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch list of prominent coaching trains with complete route data."""
        query = """
            SELECT tm.train_id, tm.train_name, tm.train_type,
                   tm.source_station_id, tm.source_station_name,
                   tm.destination_station_id, tm.destination_station_name,
                   tm.distance_km, tm.duration_hours, tm.source_type
            FROM train_master tm
            JOIN (
                SELECT train_id, count(*) as st_count
                FROM train_schedule
                GROUP BY train_id
                HAVING st_count >= 10
            ) sched ON tm.train_id = sched.train_id
            ORDER BY 
                CASE WHEN tm.train_id IN ('12951', '12004', '12002', '12952', '12301') THEN 0 ELSE 1 END,
                tm.distance_km DESC
            LIMIT ?;
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_train_info(self, train_id: str) -> Optional[Dict[str, Any]]:
        """Fetch master record for a specific train."""
        query = "SELECT * FROM train_master WHERE train_id = ? LIMIT 1;"
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (str(train_id),))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_train_schedule(self, train_id: str) -> List[Dict[str, Any]]:
        """Fetch full sequence of route stations with coordinates and timetable."""
        query = """
            SELECT ts.train_id, ts.train_name, ts.station_id, ts.station_name,
                   ts.station_sequence, ts.scheduled_arrival, ts.scheduled_departure,
                   ts.day, ts.distance_from_origin_km, ts.distance_to_next_station_km,
                   ts.latitude, ts.longitude,
                   df.dwell_time_minutes, df.scheduled_travel_time_minutes, df.hour
            FROM train_schedule ts
            LEFT JOIN derived_features df 
                   ON ts.train_id = df.train_id AND ts.station_sequence = df.station_sequence
            WHERE ts.train_id = ?
            ORDER BY ts.station_sequence ASC;
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (str(train_id),))
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                # Identify commercial halt
                arr = d.get("scheduled_arrival")
                dep = d.get("scheduled_departure")
                d["is_commercial_halt"] = (arr != dep or arr is None or dep is None)
                result.append(d)
            return result
        finally:
            conn.close()

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details for a single station."""
        query = "SELECT * FROM railway_stations WHERE station_id = ? LIMIT 1;"
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (str(station_id).upper(),))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

data_service = DataService()
