"""
Telemetry Collector Service
Ingests synthetic telemetry data (logs, metrics, config events)
and stores them for analysis by the agentic AI engine.
"""
import os
import sys
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from marshmallow import ValidationError

# Add parent directory to path for lab.common imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.schemas import (
    LogTelemetrySchema,
    MetricTelemetrySchema,
    ConfigTelemetrySchema,
    TelemetryQuerySchema,
    validate_request,
    get_validation_errors
)
from .storage.store import TelemetryStore

app = Flask(__name__)

# Secure CORS - restrict to allowed origins only
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Request-ID"],
        "expose_headers": ["X-Request-ID"]
    }
})

# Setup authentication error handlers
setup_auth_error_handlers(app)

# Initialize storage
store = TelemetryStore(storage_path=os.getenv('TELEMETRY_STORAGE_PATH', '/data/telemetry.db'))

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'telemetry_collector',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/telemetry/logs', methods=['POST'])
@require_auth
def ingest_logs():
    """Ingest log telemetry"""
    try:
        # Validate input
        data = validate_request(LogTelemetrySchema, request.json)

        # Add metadata
        data['ingested_at'] = datetime.utcnow().isoformat()
        data['telemetry_type'] = 'log'

        # Store
        telemetry_id = store.store_telemetry(data)

        return jsonify({
            'success': True,
            'telemetry_id': telemetry_id,
            'message': 'Log telemetry ingested successfully'
        }), 201
    except ValidationError as e:
        return jsonify(get_validation_errors(e)), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/metrics', methods=['POST'])
@require_auth
def ingest_metrics():
    """Ingest metric telemetry"""
    try:
        # Validate input
        data = validate_request(MetricTelemetrySchema, request.json)

        # Add metadata
        data['ingested_at'] = datetime.utcnow().isoformat()
        data['telemetry_type'] = 'metric'

        # Store
        telemetry_id = store.store_telemetry(data)

        return jsonify({
            'success': True,
            'telemetry_id': telemetry_id,
            'message': 'Metric telemetry ingested successfully'
        }), 201
    except ValidationError as e:
        return jsonify(get_validation_errors(e)), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/config', methods=['POST'])
@require_auth
def ingest_config():
    """Ingest configuration change events"""
    try:
        # Validate input
        data = validate_request(ConfigTelemetrySchema, request.json)

        # Add metadata
        data['ingested_at'] = datetime.utcnow().isoformat()
        data['telemetry_type'] = 'config'

        # Store
        telemetry_id = store.store_telemetry(data)

        return jsonify({
            'success': True,
            'telemetry_id': telemetry_id,
            'message': 'Config telemetry ingested successfully'
        }), 201
    except ValidationError as e:
        return jsonify(get_validation_errors(e)), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/query', methods=['GET'])
@require_auth
def query_telemetry():
    """Query stored telemetry"""
    try:
        telemetry_type = request.args.get('type')
        limit = int(request.args.get('limit', 100))
        since = request.args.get('since')

        results = store.query_telemetry(
            telemetry_type=telemetry_type,
            limit=limit,
            since=since
        )

        return jsonify({
            'success': True,
            'count': len(results),
            'telemetry': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get telemetry statistics"""
    try:
        stats = store.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=os.getenv('DEBUG', 'False').lower() == 'true')
