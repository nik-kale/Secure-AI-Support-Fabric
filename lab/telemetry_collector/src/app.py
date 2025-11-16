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
from lab.common.logging_config import setup_logging
from lab.common.schemas import (
    LogTelemetrySchema,
    MetricTelemetrySchema,
    ConfigTelemetrySchema,
    TelemetryQuerySchema,
    validate_request,
    validate_query_params,
    get_validation_errors
)
from .storage.store import TelemetryStore

# Setup logging
logger = setup_logging('telemetry_collector')

app = Flask(__name__)

# Security: Request size limits (1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

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


# ===================================================================
# ERROR HANDLERS
# ===================================================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle request too large errors"""
    logger.warning(f"Request too large from {request.remote_addr}")
    return jsonify({
        'success': False,
        'error': 'Request payload too large. Maximum size is 1MB.'
    }), 413


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors without exposing details"""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'An internal server error occurred. Please try again later.'
    }), 500


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Catch-all error handler"""
    logger.error(f"Unexpected error: {error}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'An unexpected error occurred. Please contact support.'
    }), 500


# ===================================================================
# HEALTH & STATUS ENDPOINTS
# ===================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'telemetry_collector',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'service': 'telemetry_collector'
        }), 503


# ===================================================================
# INGESTION ENDPOINTS
# ===================================================================

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

        logger.info(f"Log telemetry ingested: {telemetry_id}")
        return jsonify({
            'success': True,
            'telemetry_id': telemetry_id,
            'message': 'Log telemetry ingested successfully'
        }), 201

    except ValidationError as e:
        logger.warning(f"Validation error in log ingestion: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Failed to ingest log telemetry: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to ingest telemetry. Please try again later.'
        }), 500


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

        logger.info(f"Metric telemetry ingested: {telemetry_id}")
        return jsonify({
            'success': True,
            'telemetry_id': telemetry_id,
            'message': 'Metric telemetry ingested successfully'
        }), 201

    except ValidationError as e:
        logger.warning(f"Validation error in metric ingestion: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Failed to ingest metric telemetry: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to ingest telemetry. Please try again later.'
        }), 500


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

        logger.info(f"Config telemetry ingested: {telemetry_id}")
        return jsonify({
            'success': True,
            'telemetry_id': telemetry_id,
            'message': 'Config telemetry ingested successfully'
        }), 201

    except ValidationError as e:
        logger.warning(f"Validation error in config ingestion: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Failed to ingest config telemetry: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to ingest telemetry. Please try again later.'
        }), 500


# ===================================================================
# QUERY ENDPOINTS
# ===================================================================

@app.route('/api/telemetry/query', methods=['GET'])
@require_auth
def query_telemetry():
    """Query stored telemetry"""
    try:
        # Validate query parameters
        validated_params = validate_query_params(TelemetryQuerySchema, request.args)

        logger.debug(f"Querying telemetry with params: {validated_params}")

        results = store.query_telemetry(
            telemetry_type=validated_params.get('type'),
            limit=validated_params.get('limit', 100),
            since=validated_params.get('since')
        )

        return jsonify({
            'success': True,
            'count': len(results),
            'telemetry': results
        }), 200

    except ValidationError as e:
        logger.warning(f"Validation error in query: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Failed to query telemetry: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to query telemetry. Please try again later.'
        }), 500


@app.route('/api/telemetry/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get telemetry statistics"""
    try:
        logger.debug("Fetching telemetry statistics")

        stats = store.get_statistics()

        return jsonify({
            'success': True,
            'statistics': stats
        }), 200

    except Exception as e:
        logger.error(f"Failed to fetch statistics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve statistics. Please try again later.'
        }), 500


if __name__ == '__main__':
    logger.info("Starting Telemetry Collector API server on port 8081")
    app.run(
        host='0.0.0.0',
        port=8081,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
