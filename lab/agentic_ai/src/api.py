"""
REST API for the Agentic AI engine
"""
import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from marshmallow import ValidationError

# Add parent directory to path for lab.common imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.logging_config import setup_logging
from lab.common.tracing import setup_tracing
from lab.common.schemas import (
    FindingsQuerySchema,
    RemediationQuerySchema,
    RemediationRequestSchema,
    AnalysisRequestSchema,
    validate_query_params,
    validate_request,
    get_validation_errors
)
from .engine import AIEngine

# Setup logging
logger = setup_logging('agentic_ai')

app = Flask(__name__)
setup_tracing('agentic_ai', app)

# Security: Request size limits (1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

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
            'service': 'agentic_ai',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'service': 'agentic_ai'
        }), 503


# ===================================================================
# ANALYSIS ENDPOINTS
# ===================================================================

@app.route('/api/analyze', methods=['POST'])
@require_auth
def analyze():
    """Run full analysis and remediation cycle"""
    try:
        # Validate request body if provided
        data = request.json or {}
        if data:
            validated_data = validate_request(AnalysisRequestSchema, data)
        else:
            validated_data = {}

        logger.info(f"Starting analysis cycle with params: {validated_data}")

        result = ai_engine.analyze_and_remediate()

        logger.info(f"Analysis completed successfully")
        return jsonify({
            'success': True,
            'result': result
        }), 200

    except ValidationError as e:
        logger.warning(f"Validation error in analyze: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Analysis failed. Please check system health and try again.'
        }), 500


@app.route('/api/detect', methods=['POST'])
@require_auth
def detect():
    """Run detection only (no remediation)"""
    try:
        logger.info("Starting detection cycle")

        findings = ai_engine.run_detection()

        logger.info(f"Detection completed: {len(findings)} findings")
        return jsonify({
            'success': True,
            'findings_count': len(findings),
            'findings': [f.to_dict() for f in findings]
        }), 200

    except Exception as e:
        logger.error(f"Detection failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Detection failed. Please check system health and try again.'
        }), 500


# ===================================================================
# QUERY ENDPOINTS
# ===================================================================

@app.route('/api/findings', methods=['GET'])
@require_auth
def get_findings():
    """Get detected findings"""
    try:
        # Validate query parameters
        validated_params = validate_query_params(FindingsQuerySchema, request.args)

        logger.debug(f"Fetching findings with params: {validated_params}")

        findings = ai_engine.get_findings(limit=validated_params.get('limit', 20))

        return jsonify({
            'success': True,
            'count': len(findings),
            'findings': findings
        }), 200

    except ValidationError as e:
        logger.warning(f"Validation error in get_findings: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Failed to fetch findings: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve findings. Please try again later.'
        }), 500


@app.route('/api/remediation', methods=['GET'])
@require_auth
def get_remediation():
    """Get remediation plans"""
    try:
        # Validate query parameters
        validated_params = validate_query_params(RemediationQuerySchema, request.args)

        logger.debug(f"Fetching remediation plans with params: {validated_params}")

        plans = ai_engine.get_remediation_plans(limit=validated_params.get('limit', 20))

        return jsonify({
            'success': True,
            'count': len(plans),
            'remediation_plans': plans
        }), 200

    except ValidationError as e:
        logger.warning(f"Validation error in get_remediation: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Failed to fetch remediation plans: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve remediation plans. Please try again later.'
        }), 500


# ===================================================================
# REMEDIATION ENDPOINTS
# ===================================================================

@app.route('/api/remediate', methods=['POST'])
@require_auth
def remediate():
    """Generate remediation plans for existing findings"""
    try:
        # Validate request body
        data = request.json or {}

        if data.get('finding_ids'):
            validated_data = validate_request(RemediationRequestSchema, data)
            finding_ids = validated_data['finding_ids']

            logger.info(f"Generating remediation for {len(finding_ids)} specific findings")

            # Filter findings by IDs
            all_findings = ai_engine.get_findings(limit=100)
            selected_findings = [
                f for f in all_findings
                if f.get('finding_id') in finding_ids
            ]

            if not selected_findings:
                logger.warning(f"No findings found matching provided IDs")
                return jsonify({
                    'success': False,
                    'error': 'No findings found with the provided IDs'
                }), 404

            # Generate remediation plans
            plans = []
            for finding_dict in selected_findings:
                plan = ai_engine.remediation_engine.generate_plan(finding_dict)
                plans.append(plan)
        else:
            # Generate for all cached findings
            logger.info("Generating remediation for all cached findings")
            plans = ai_engine.generate_remediation_plans()

        logger.info(f"Generated {len(plans)} remediation plans")
        return jsonify({
            'success': True,
            'remediation_plans_count': len(plans),
            'remediation_plans': [p.to_dict() for p in plans]
        }), 200

    except ValidationError as e:
        logger.warning(f"Validation error in remediate: {e.messages}")
        return jsonify(get_validation_errors(e)), 400

    except Exception as e:
        logger.error(f"Remediation generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate remediation plans. Please try again later.'
        }), 500


if __name__ == '__main__':
    logger.info(f"Starting Agentic AI API server on port 8082")
    app.run(
        host='0.0.0.0',
        port=8082,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
