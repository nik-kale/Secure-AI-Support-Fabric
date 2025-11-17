"""
Full-text Log Search Engine (V2.7)
Advanced log search with indexing and filtering
"""
import os
import sys
import json
import sqlite3
import threading
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Any, Optional
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging
from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.security_headers import setup_security_headers
from lab.common.rate_limit import rate_limit

logger = setup_logging('log_search')

app = Flask(__name__)

# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB for log batches

# CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Setup security
setup_auth_error_handlers(app)
setup_security_headers(app)

# Storage
STORAGE_PATH = os.getenv('LOG_STORAGE_PATH', '/data/logs.db')


class LogSearchEngine:
    """Full-text search engine for logs with FTS5"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def connection(self):
        """Thread-local connection with WAL mode"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0,
                isolation_level=None
            )
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=-20000')  # 20MB cache
            conn.execute('PRAGMA temp_store=MEMORY')
            self._local.connection = conn
            logger.debug(f"Created log search connection for thread {threading.get_ident()}")
        return self._local.connection

    def _init_db(self):
        """Initialize database with FTS5 for full-text search"""
        conn = self.connection
        cursor = conn.cursor()

        # Main logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                level TEXT NOT NULL,
                service TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                trace_id TEXT,
                span_id TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # FTS5 virtual table for full-text search
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS logs_fts USING fts5(
                message,
                service,
                level,
                context,
                content=logs,
                content_rowid=id
            )
        ''')

        # Triggers to keep FTS index in sync
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS logs_ai AFTER INSERT ON logs BEGIN
                INSERT INTO logs_fts(rowid, message, service, level, context)
                VALUES (new.id, new.message, new.service, new.level, new.context);
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS logs_ad AFTER DELETE ON logs BEGIN
                DELETE FROM logs_fts WHERE rowid = old.id;
            END
        ''')

        # Indexes for common queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_service ON logs(service)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_level ON logs(level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trace_id ON logs(trace_id)')

        logger.info("Log search engine database initialized with FTS5")

    def ingest_log(self, log_entry: Dict) -> bool:
        """Ingest a single log entry"""
        try:
            conn = self.connection
            cursor = conn.cursor()

            timestamp = log_entry.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = int(datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp() * 1_000_000_000)
            elif timestamp is None:
                timestamp = int(datetime.utcnow().timestamp() * 1_000_000_000)

            cursor.execute('''
                INSERT INTO logs (timestamp, level, service, message, context, trace_id, span_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                log_entry.get('level', 'INFO'),
                log_entry.get('service', 'unknown'),
                log_entry.get('message', ''),
                log_entry.get('context', ''),
                log_entry.get('trace_id'),
                log_entry.get('span_id'),
                json.dumps(log_entry.get('metadata', {}))
            ))

            return True

        except Exception as e:
            logger.error(f"Failed to ingest log: {e}", exc_info=True)
            return False

    def search(
        self,
        query: str = None,
        service: str = None,
        level: str = None,
        trace_id: str = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Search logs with various filters"""
        conn = self.connection
        cursor = conn.cursor()

        # Build query
        if query:
            # Full-text search
            sql = '''
                SELECT logs.* FROM logs
                INNER JOIN logs_fts ON logs.id = logs_fts.rowid
                WHERE logs_fts MATCH ?
            '''
            params = [query]
        else:
            sql = 'SELECT * FROM logs WHERE 1=1'
            params = []

        # Add filters
        if service:
            sql += ' AND service = ?'
            params.append(service)

        if level:
            sql += ' AND level = ?'
            params.append(level)

        if trace_id:
            sql += ' AND trace_id = ?'
            params.append(trace_id)

        if start_time:
            sql += ' AND timestamp >= ?'
            params.append(start_time)

        if end_time:
            sql += ' AND timestamp <= ?'
            params.append(end_time)

        # Order and limit
        sql += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'level': row[2],
                'service': row[3],
                'message': row[4],
                'context': row[5],
                'trace_id': row[6],
                'span_id': row[7],
                'metadata': json.loads(row[8]) if row[8] else {}
            })

        return results

    def get_log_stats(self, start_time: int = None, end_time: int = None) -> Dict:
        """Get log statistics"""
        conn = self.connection
        cursor = conn.cursor()

        sql_where = ''
        params = []

        if start_time:
            sql_where += ' WHERE timestamp >= ?'
            params.append(start_time)

        if end_time:
            if sql_where:
                sql_where += ' AND timestamp <= ?'
            else:
                sql_where = ' WHERE timestamp <= ?'
            params.append(end_time)

        # Total count
        cursor.execute(f'SELECT COUNT(*) FROM logs{sql_where}', params)
        total_count = cursor.fetchone()[0]

        # Count by level
        cursor.execute(f'SELECT level, COUNT(*) FROM logs{sql_where} GROUP BY level', params)
        by_level = dict(cursor.fetchall())

        # Count by service
        cursor.execute(f'SELECT service, COUNT(*) FROM logs{sql_where} GROUP BY service ORDER BY COUNT(*) DESC LIMIT 10', params)
        by_service = dict(cursor.fetchall())

        # Recent errors
        cursor.execute(f'''
            SELECT message, COUNT(*) as count FROM logs
            {sql_where}{"AND" if sql_where else "WHERE"} level IN ('ERROR', 'CRITICAL')
            GROUP BY message
            ORDER BY count DESC
            LIMIT 5
        ''', params)
        top_errors = [{'message': row[0], 'count': row[1]} for row in cursor.fetchall()]

        return {
            'total_count': total_count,
            'by_level': by_level,
            'by_service': by_service,
            'top_errors': top_errors
        }

    def get_log_patterns(self, limit: int = 20) -> List[Dict]:
        """Extract common log patterns"""
        conn = self.connection
        cursor = conn.cursor()

        # Get recent error messages
        cursor.execute('''
            SELECT message, COUNT(*) as count
            FROM logs
            WHERE level IN ('ERROR', 'WARNING')
            AND timestamp > ?
            GROUP BY message
            ORDER BY count DESC
            LIMIT ?
        ''', (int((datetime.utcnow() - timedelta(hours=24)).timestamp() * 1_000_000_000), limit))

        patterns = []
        for message, count in cursor.fetchall():
            # Extract pattern by replacing numbers/UUIDs with placeholders
            pattern = re.sub(r'\b\d+\b', '<NUM>', message)
            pattern = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<UUID>', pattern, flags=re.IGNORECASE)
            pattern = re.sub(r'\b[0-9a-f]{32,}\b', '<HASH>', pattern, flags=re.IGNORECASE)

            patterns.append({
                'pattern': pattern,
                'example': message,
                'count': count
            })

        return patterns


# Initialize search engine
search_engine = LogSearchEngine(STORAGE_PATH)


# ===================================================================
# API ENDPOINTS
# ===================================================================

@app.route('/api/logs/ingest', methods=['POST'])
@rate_limit(tier='ingest', max_requests=10000, window_seconds=3600)
@require_auth
def ingest_logs():
    """Ingest log entries"""
    try:
        data = request.json

        if isinstance(data, list):
            # Batch ingestion
            success_count = 0
            for log_entry in data:
                if search_engine.ingest_log(log_entry):
                    success_count += 1

            return jsonify({
                'success': True,
                'ingested': success_count,
                'total': len(data)
            }), 200
        else:
            # Single log entry
            success = search_engine.ingest_log(data)

            return jsonify({
                'success': success
            }), 200 if success else 500

    except Exception as e:
        logger.error(f"Failed to ingest logs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to process logs'
        }), 500


@app.route('/api/logs/search', methods=['GET'])
@rate_limit(tier='query', max_requests=1000, window_seconds=3600)
@require_auth
def search_logs():
    """Search logs with full-text search"""
    try:
        query = request.args.get('query')  # FTS query (e.g., "error AND database")
        service = request.args.get('service')
        level = request.args.get('level')
        trace_id = request.args.get('trace_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        # Time range
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        if start_time:
            start_time = int(start_time)
        if end_time:
            end_time = int(end_time)

        logs = search_engine.search(
            query=query,
            service=service,
            level=level,
            trace_id=trace_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'success': True,
            'count': len(logs),
            'logs': logs,
            'offset': offset,
            'limit': limit
        }), 200

    except Exception as e:
        logger.error(f"Failed to search logs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500


@app.route('/api/logs/stats', methods=['GET'])
@rate_limit(tier='query', max_requests=100, window_seconds=3600)
@require_auth
def get_stats():
    """Get log statistics"""
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        if start_time:
            start_time = int(start_time)
        if end_time:
            end_time = int(end_time)

        stats = search_engine.get_log_stats(start_time, end_time)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve statistics'
        }), 500


@app.route('/api/logs/patterns', methods=['GET'])
@rate_limit(tier='query', max_requests=100, window_seconds=3600)
@require_auth
def get_patterns():
    """Get common log patterns"""
    try:
        limit = int(request.args.get('limit', 20))

        patterns = search_engine.get_log_patterns(limit)

        return jsonify({
            'success': True,
            'patterns': patterns
        }), 200

    except Exception as e:
        logger.error(f"Failed to get patterns: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to extract patterns'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'log_search',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    logger.info("Starting Log Search Engine on port 8086")
    app.run(
        host='0.0.0.0',
        port=8086,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
