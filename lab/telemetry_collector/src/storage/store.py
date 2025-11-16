"""
Telemetry storage module using SQLite with proper error handling and connection pooling
"""
import sqlite3
import json
import uuid
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger('telemetry_collector.store')


class TelemetryStore:
    """SQLite-based telemetry storage with connection pooling and error handling"""

    def __init__(self, storage_path: str = '/data/telemetry.db'):
        self.storage_path = storage_path
        self._local = threading.local()
        self._init_db()

    @property
    def connection(self):
        """Thread-local connection for connection pooling"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.storage_path,
                check_same_thread=False,
                timeout=10.0
            )
        return self._local.connection

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with automatic rollback on error"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database operation failed: {e}", exc_info=True)
            raise
        finally:
            cursor.close()

    def _init_db(self):
        """Initialize database schema with error handling"""
        try:
            with self.get_cursor() as cursor:
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

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise

    def store_telemetry(self, data: Dict[str, Any]) -> str:
        """
        Store telemetry data with error handling

        Args:
            data: Telemetry data dictionary

        Returns:
            Telemetry ID

        Raises:
            ValueError: If data is invalid
            sqlite3.Error: If database operation fails
        """
        if not data:
            raise ValueError("Telemetry data cannot be empty")

        telemetry_id = str(uuid.uuid4())
        telemetry_type = data.get('telemetry_type', 'unknown')
        ingested_at = data.get('ingested_at', datetime.utcnow().isoformat())

        try:
            with self.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO telemetry (id, telemetry_type, ingested_at, data)
                    VALUES (?, ?, ?, ?)
                ''', (telemetry_id, telemetry_type, ingested_at, json.dumps(data)))

            logger.debug(f"Stored telemetry: {telemetry_id}")
            return telemetry_id

        except json.JSONEncodeError as e:
            logger.error(f"Failed to JSON encode telemetry data: {e}")
            raise ValueError(f"Invalid telemetry data format: {e}")
        except Exception as e:
            logger.error(f"Failed to store telemetry: {e}", exc_info=True)
            raise

    def query_telemetry(
        self,
        telemetry_type: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query telemetry data with error handling

        Args:
            telemetry_type: Filter by telemetry type
            limit: Maximum number of results (1-1000)
            since: Filter by timestamp (ISO format)

        Returns:
            List of telemetry entries

        Raises:
            ValueError: If parameters are invalid
            sqlite3.Error: If database query fails
        """
        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")

        try:
            with self.get_cursor() as cursor:
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

            results = []
            for row in rows:
                try:
                    results.append({
                        'id': row[0],
                        'telemetry_type': row[1],
                        'ingested_at': row[2],
                        'data': json.loads(row[3])
                    })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to decode telemetry {row[0]}: {e}")
                    continue

            logger.debug(f"Queried {len(results)} telemetry entries")
            return results

        except Exception as e:
            logger.error(f"Failed to query telemetry: {e}", exc_info=True)
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get telemetry statistics with error handling

        Returns:
            Dictionary containing statistics

        Raises:
            sqlite3.Error: If database query fails
        """
        try:
            with self.get_cursor() as cursor:
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

            logger.debug("Retrieved telemetry statistics")
            return {
                'total_count': total_count,
                'count_by_type': type_counts,
                'latest_telemetry': latest
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            raise

    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            try:
                self._local.connection.close()
                delattr(self._local, 'connection')
                logger.debug("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
