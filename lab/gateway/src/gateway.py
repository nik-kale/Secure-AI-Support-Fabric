"""
API Gateway Service
Routes requests to appropriate services and handles context propagation
"""
import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Service URLs
TELEMETRY_COLLECTOR_URL = os.getenv('TELEMETRY_COLLECTOR_URL', 'http://telemetry_collector:8081')
AGENTIC_AI_URL = os.getenv('AGENTIC_AI_URL', 'http://agentic_ai:8082')
UI_DASH_URL = os.getenv('UI_DASH_URL', 'http://ui_dash:3000')


def add_context_headers(headers: dict = None) -> dict:
    """Add tracing and context headers"""
    if headers is None:
        headers = {}

    # Add request ID if not present
    if 'X-Request-ID' not in headers:
        headers['X-Request-ID'] = str(uuid.uuid4())

    # Add timestamp
    headers['X-Gateway-Timestamp'] = datetime.utcnow().isoformat()

    return headers


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    # Check health of all services
    services = {}

    try:
        resp = requests.get(f'{TELEMETRY_COLLECTOR_URL}/health', timeout=2)
        services['telemetry_collector'] = 'healthy' if resp.status_code == 200 else 'unhealthy'
    except Exception:
        services['telemetry_collector'] = 'unreachable'

    try:
        resp = requests.get(f'{AGENTIC_AI_URL}/health', timeout=2)
        services['agentic_ai'] = 'healthy' if resp.status_code == 200 else 'unhealthy'
    except Exception:
        services['agentic_ai'] = 'unreachable'

    all_healthy = all(status == 'healthy' for status in services.values())

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'service': 'gateway',
        'timestamp': datetime.utcnow().isoformat(),
        'services': services
    }), 200 if all_healthy else 503


# Telemetry routes
@app.route('/api/telemetry/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_telemetry(subpath):
    """Proxy requests to telemetry collector"""
    try:
        headers = add_context_headers(dict(request.headers))

        url = f'{TELEMETRY_COLLECTOR_URL}/api/telemetry/{subpath}'

        if request.method == 'GET':
            resp = requests.get(url, params=request.args, headers=headers, timeout=10)
        elif request.method == 'POST':
            resp = requests.post(url, json=request.json, headers=headers, timeout=10)
        elif request.method == 'PUT':
            resp = requests.put(url, json=request.json, headers=headers, timeout=10)
        else:  # DELETE
            resp = requests.delete(url, headers=headers, timeout=10)

        return jsonify(resp.json()), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Telemetry service timeout'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Telemetry service unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# AI engine routes
@app.route('/api/ai/<path:subpath>', methods=['GET', 'POST'])
def proxy_ai(subpath):
    """Proxy requests to agentic AI engine"""
    try:
        headers = add_context_headers(dict(request.headers))

        url = f'{AGENTIC_AI_URL}/api/{subpath}'

        if request.method == 'GET':
            resp = requests.get(url, params=request.args, headers=headers, timeout=30)
        else:  # POST
            resp = requests.post(url, json=request.json, headers=headers, timeout=30)

        return jsonify(resp.json()), resp.status_code

    except requests.exceptions.Timeout:
        return jsonify({'error': 'AI service timeout'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'AI service unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Convenience endpoints
@app.route('/api/status', methods=['GET'])
def get_status():
    """Get overall system status"""
    try:
        # Get telemetry stats
        headers = add_context_headers()
        telemetry_resp = requests.get(
            f'{TELEMETRY_COLLECTOR_URL}/api/telemetry/stats',
            headers=headers,
            timeout=5
        )
        telemetry_stats = telemetry_resp.json() if telemetry_resp.status_code == 200 else {}

        # Get AI findings
        ai_resp = requests.get(
            f'{AGENTIC_AI_URL}/api/findings?limit=10',
            headers=headers,
            timeout=5
        )
        ai_findings = ai_resp.json() if ai_resp.status_code == 200 else {}

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'telemetry': telemetry_stats,
            'ai_findings': ai_findings
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/run-analysis', methods=['POST'])
def run_analysis():
    """Trigger a full analysis cycle"""
    try:
        headers = add_context_headers()

        # Trigger AI analysis
        resp = requests.post(
            f'{AGENTIC_AI_URL}/api/analyze',
            headers=headers,
            timeout=30
        )

        return jsonify(resp.json()), resp.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
