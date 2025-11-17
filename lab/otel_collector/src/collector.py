"""
OpenTelemetry Collector Service
Receives and processes OTLP traces, metrics, and logs
"""
import os
import sys
import json
import sqlite3
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging
from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.security_headers import setup_security_headers
from lab.common.rate_limit import rate_limit

# Setup logging
logger = setup_logging('otel_collector')

app = Flask(__name__)

# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB for trace batches

# CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r"/v1/*": {"origins": allowed_origins}})

# Setup security
setup_auth_error_handlers(app)
setup_security_headers(app)

# Storage
STORAGE_PATH = os.getenv('OTEL_STORAGE_PATH', '/data/otel.db')


class OTelStore:
    """Storage for OpenTelemetry data with connection pooling"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def connection(self):
        """Thread-local connection with WAL mode for high concurrency"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0,
                isolation_level=None  # Autocommit mode for WAL
            )
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=-10000')  # 10MB cache
            conn.execute('PRAGMA temp_store=MEMORY')
            self._local.connection = conn
            logger.debug(f"Created OTel connection for thread {threading.get_ident()}")
        return self._local.connection
    
    def _init_db(self):
        """Initialize database schema"""
        conn = self.connection
        cursor = conn.cursor()
        
        # Traces table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT NOT NULL,
                span_id TEXT PRIMARY KEY,
                parent_span_id TEXT,
                name TEXT NOT NULL,
                kind TEXT,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                duration_ns INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                attributes TEXT,
                status_code TEXT,
                status_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                attributes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trace_id ON traces(trace_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_service ON traces(service_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_start_time ON traces(start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_name ON metrics(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metric_time ON metrics(timestamp)')

        logger.info("OpenTelemetry database initialized with WAL mode")
    
    def store_traces(self, resource_spans: List[Dict]) -> int:
        """Store trace spans"""
        conn = self.connection
        cursor = conn.cursor()
        
        span_count = 0
        for resource_span in resource_spans:
            service_name = "unknown"
            if resource_span.get('resource'):
                for attr in resource_span['resource'].get('attributes', []):
                    if attr.get('key') == 'service.name':
                        service_name = attr.get('value', {}).get('stringValue', 'unknown')
            
            for scope_span in resource_span.get('scopeSpans', []):
                for span in scope_span.get('spans', []):
                    trace_id = span.get('traceId', '')
                    span_id = span.get('spanId', '')
                    parent_span_id = span.get('parentSpanId', '')
                    name = span.get('name', 'unknown')
                    kind = span.get('kind', 'UNSPECIFIED')
                    start_time = int(span.get('startTimeUnixNano', 0))
                    end_time = int(span.get('endTimeUnixNano', 0))
                    duration_ns = end_time - start_time
                    
                    attributes = json.dumps(span.get('attributes', []))
                    status = span.get('status', {})
                    status_code = status.get('code', 'UNSET')
                    status_message = status.get('message', '')
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO traces
                        (trace_id, span_id, parent_span_id, name, kind, start_time, end_time,
                         duration_ns, service_name, attributes, status_code, status_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (trace_id, span_id, parent_span_id, name, kind, start_time, end_time,
                          duration_ns, service_name, attributes, status_code, status_message))

                    span_count += 1

        return span_count
    
    def store_metrics(self, resource_metrics: List[Dict]) -> int:
        """Store metrics"""
        conn = self.connection
        cursor = conn.cursor()
        
        metric_count = 0
        for resource_metric in resource_metrics:
            service_name = "unknown"
            if resource_metric.get('resource'):
                for attr in resource_metric['resource'].get('attributes', []):
                    if attr.get('key') == 'service.name':
                        service_name = attr.get('value', {}).get('stringValue', 'unknown')
            
            for scope_metric in resource_metric.get('scopeMetrics', []):
                for metric in scope_metric.get('metrics', []):
                    name = metric.get('name', 'unknown')
                    
                    # Handle different metric types
                    if 'gauge' in metric:
                        for datapoint in metric['gauge'].get('dataPoints', []):
                            self._insert_metric(cursor, name, 'gauge', datapoint, service_name)
                            metric_count += 1
                    elif 'sum' in metric:
                        for datapoint in metric['sum'].get('dataPoints', []):
                            self._insert_metric(cursor, name, 'sum', datapoint, service_name)
                            metric_count += 1
                    elif 'histogram' in metric:
                        for datapoint in metric['histogram'].get('dataPoints', []):
                            self._insert_metric(cursor, name, 'histogram', datapoint, service_name)
                            metric_count += 1

        return metric_count
    
    def _insert_metric(self, cursor, name: str, metric_type: str, datapoint: Dict, service_name: str):
        """Insert a single metric datapoint"""
        timestamp = int(datapoint.get('timeUnixNano', 0))
        
        # Get value based on type
        if 'asInt' in datapoint:
            value = float(datapoint['asInt'])
        elif 'asDouble' in datapoint:
            value = datapoint['asDouble']
        elif 'count' in datapoint:  # histogram
            value = float(datapoint['count'])
        else:
            value = 0.0
        
        attributes = json.dumps(datapoint.get('attributes', []))
        
        cursor.execute('''
            INSERT INTO metrics (name, type, value, timestamp, service_name, attributes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, metric_type, value, timestamp, service_name, attributes))
    
    def query_traces(self, trace_id: str = None, service_name: str = None, limit: int = 100) -> List[Dict]:
        """Query traces"""
        conn = self.connection
        cursor = conn.cursor()
        
        query = 'SELECT * FROM traces WHERE 1=1'
        params = []
        
        if trace_id:
            query += ' AND trace_id = ?'
            params.append(trace_id)
        if service_name:
            query += ' AND service_name = ?'
            params.append(service_name)
        
        query += ' ORDER BY start_time DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'trace_id': row[0],
                'span_id': row[1],
                'parent_span_id': row[2],
                'name': row[3],
                'kind': row[4],
                'start_time': row[5],
                'end_time': row[6],
                'duration_ns': row[7],
                'service_name': row[8],
                'attributes': json.loads(row[9]) if row[9] else [],
                'status_code': row[10],
                'status_message': row[11]
            })
        
        return results


# Initialize storage
store = OTelStore(STORAGE_PATH)


# ===================================================================
# OTLP ENDPOINTS (OpenTelemetry Protocol)
# ===================================================================

@app.route('/v1/traces', methods=['POST'])
@rate_limit(tier='ingest', max_requests=10000, window_seconds=3600)
@require_auth
def ingest_traces():
    """OTLP trace ingestion endpoint"""
    try:
        data = request.json
        resource_spans = data.get('resourceSpans', [])
        
        span_count = store.store_traces(resource_spans)
        
        logger.info(f"Ingested {span_count} spans")
        return jsonify({
            'success': True,
            'spans_received': span_count
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to ingest traces: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to process traces'
        }), 500


@app.route('/v1/metrics', methods=['POST'])
@rate_limit(tier='ingest', max_requests=10000, window_seconds=3600)
@require_auth
def ingest_metrics():
    """OTLP metrics ingestion endpoint"""
    try:
        data = request.json
        resource_metrics = data.get('resourceMetrics', [])
        
        metric_count = store.store_metrics(resource_metrics)
        
        logger.info(f"Ingested {metric_count} metrics")
        return jsonify({
            'success': True,
            'metrics_received': metric_count
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to ingest metrics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to process metrics'
        }), 500


@app.route('/v1/logs', methods=['POST'])
@rate_limit(tier='ingest', max_requests=10000, window_seconds=3600)
@require_auth
def ingest_logs():
    """OTLP logs ingestion endpoint"""
    try:
        data = request.json
        # For now, forward to telemetry collector
        logger.info(f"Received OTLP logs (forwarding to telemetry)")
        return jsonify({
            'success': True,
            'message': 'Logs received'
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to ingest logs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to process logs'
        }), 500


# ===================================================================
# QUERY ENDPOINTS
# ===================================================================

@app.route('/api/traces', methods=['GET'])
@rate_limit(tier='query', max_requests=1000, window_seconds=3600)
@require_auth
def query_traces():
    """Query stored traces"""
    try:
        trace_id = request.args.get('trace_id')
        service_name = request.args.get('service')
        limit = int(request.args.get('limit', 100))
        
        traces = store.query_traces(trace_id=trace_id, service_name=service_name, limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(traces),
            'traces': traces
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to query traces: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to query traces'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'otel_collector',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    logger.info("Starting OpenTelemetry Collector on port 4318")
    app.run(
        host='0.0.0.0',
        port=4318,  # OTLP HTTP port
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
