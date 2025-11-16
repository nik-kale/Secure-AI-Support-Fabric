"""
REST API for the Agentic AI engine
"""
import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path for lab.common imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.auth import require_auth, setup_auth_error_handlers
from .engine import AIEngine

app = Flask(__name__)

# Secure CORS - restrict to allowed origins only
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Request-ID"],
        "expose_headers": ["X-Request-ID"]
    }
})

# Setup authentication error handlers
setup_auth_error_handlers(app)

# Initialize AI engine
ai_engine = AIEngine()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'agentic_ai',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/analyze', methods=['POST'])
@require_auth
def analyze():
    """Run full analysis and remediation cycle"""
    try:
        result = ai_engine.analyze_and_remediate()
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/findings', methods=['GET'])
@require_auth
def get_findings():
    """Get detected findings"""
    try:
        limit = int(request.args.get('limit', 50))
        findings = ai_engine.get_findings(limit=limit)

        return jsonify({
            'success': True,
            'count': len(findings),
            'findings': findings
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/remediation', methods=['GET'])
@require_auth
def get_remediation():
    """Get remediation plans"""
    try:
        limit = int(request.args.get('limit', 50))
        plans = ai_engine.get_remediation_plans(limit=limit)

        return jsonify({
            'success': True,
            'count': len(plans),
            'remediation_plans': plans
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/detect', methods=['POST'])
@require_auth
def detect():
    """Run detection only (no remediation)"""
    try:
        findings = ai_engine.run_detection()

        return jsonify({
            'success': True,
            'findings_count': len(findings),
            'findings': [f.to_dict() for f in findings]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/remediate', methods=['POST'])
@require_auth
def remediate():
    """Generate remediation plans for existing findings"""
    try:
        # Optionally accept finding IDs in request body
        data = request.json or {}
        finding_ids = data.get('finding_ids')

        if finding_ids:
            # Filter findings by IDs
            all_findings = ai_engine.get_findings(limit=100)
            selected_findings = [
                f for f in all_findings
                if f.get('finding_id') in finding_ids
            ]
            # Convert back to Finding objects (simplified - just use dicts)
            plans = []
            for finding_dict in selected_findings:
                plan = ai_engine.remediation_engine.generate_plan(finding_dict)
                plans.append(plan)
        else:
            # Generate for all cached findings
            plans = ai_engine.generate_remediation_plans()

        return jsonify({
            'success': True,
            'remediation_plans_count': len(plans),
            'remediation_plans': [p.to_dict() for p in plans]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8082,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
