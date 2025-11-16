"""
Telemetry Collector Service
Ingests synthetic telemetry data (logs, metrics, config events)
and stores them for analysis by the agentic AI engine.
"""
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from storage.store import TelemetryStore

app = Flask(__name__)
CORS(app)

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
def ingest_logs():
    """Ingest log telemetry"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/metrics', methods=['POST'])
def ingest_metrics():
    """Ingest metric telemetry"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/config', methods=['POST'])
def ingest_config():
    """Ingest configuration change events"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telemetry/query', methods=['GET'])
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
