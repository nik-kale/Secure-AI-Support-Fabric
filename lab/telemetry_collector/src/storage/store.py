"""
Telemetry storage module using SQLite for simplicity
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

class TelemetryStore:
    """Simple SQLite-based telemetry storage"""

    def __init__(self, storage_path: str = '/data/telemetry.db'):
        self.storage_path = storage_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry (
                id TEXT PRIMARY KEY,
                telemetry_type TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_telemetry_type
            ON telemetry(telemetry_type)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ingested_at
            ON telemetry(ingested_at)
        ''')

        conn.commit()
        conn.close()

    def store_telemetry(self, data: Dict[str, Any]) -> str:
        """Store telemetry data"""
        telemetry_id = str(uuid.uuid4())
        telemetry_type = data.get('telemetry_type', 'unknown')
        ingested_at = data.get('ingested_at', datetime.utcnow().isoformat())

        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO telemetry (id, telemetry_type, ingested_at, data)
            VALUES (?, ?, ?, ?)
        ''', (telemetry_id, telemetry_type, ingested_at, json.dumps(data)))

        conn.commit()
        conn.close()

        return telemetry_id

    def query_telemetry(
        self,
        telemetry_type: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query telemetry data"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()

        query = 'SELECT id, telemetry_type, ingested_at, data FROM telemetry WHERE 1=1'
        params = []

        if telemetry_type:
            query += ' AND telemetry_type = ?'
            params.append(telemetry_type)

        if since:
            query += ' AND ingested_at >= ?'
            params.append(since)

        query += ' ORDER BY ingested_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'telemetry_type': row[1],
                'ingested_at': row[2],
                'data': json.loads(row[3])
            })

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get telemetry statistics"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()

        # Total count
        cursor.execute('SELECT COUNT(*) FROM telemetry')
        total_count = cursor.fetchone()[0]

        # Count by type
        cursor.execute('''
            SELECT telemetry_type, COUNT(*)
            FROM telemetry
            GROUP BY telemetry_type
        ''')
        type_counts = dict(cursor.fetchall())

        # Latest telemetry
        cursor.execute('''
            SELECT MAX(ingested_at) FROM telemetry
        ''')
        latest = cursor.fetchone()[0]

        conn.close()

        return {
            'total_count': total_count,
            'count_by_type': type_counts,
            'latest_telemetry': latest
        }
