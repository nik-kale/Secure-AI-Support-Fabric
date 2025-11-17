"""
Distributed Tracing Visualization Service
Web-based UI for analyzing OpenTelemetry traces
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging
from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.security_headers import setup_security_headers
from lab.common.rate_limit import rate_limit

logger = setup_logging('trace_visualizer')

app = Flask(__name__)

# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB

# CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Setup security
setup_auth_error_handlers(app)
setup_security_headers(app)

# OTel collector URL
OTEL_COLLECTOR_URL = os.getenv('OTEL_COLLECTOR_URL', 'http://otel_collector:4318')


class TraceAnalyzer:
    """Analyzes and structures trace data for visualization"""

    @staticmethod
    def build_trace_tree(spans: List[Dict]) -> Dict:
        """Build hierarchical trace tree from flat span list"""
        if not spans:
            return {}

        # Index spans by span_id
        span_map = {span['span_id']: span for span in spans}

        # Find root span (no parent)
        root_span = None
        for span in spans:
            if not span.get('parent_span_id') or span['parent_span_id'] not in span_map:
                root_span = span
                break

        if not root_span:
            root_span = spans[0]

        # Build tree recursively
        def add_children(span: Dict) -> Dict:
            span_with_children = span.copy()
            span_with_children['children'] = []

            for other_span in spans:
                if other_span.get('parent_span_id') == span['span_id']:
                    child = add_children(other_span)
                    span_with_children['children'].append(child)

            return span_with_children

        trace_tree = add_children(root_span)

        # Calculate trace metadata
        all_start_times = [s['start_time'] for s in spans]
        all_end_times = [s['end_time'] for s in spans]

        trace_metadata = {
            'trace_id': root_span.get('trace_id'),
            'root_service': root_span.get('service_name'),
            'span_count': len(spans),
            'total_duration_ns': max(all_end_times) - min(all_start_times),
            'services': list(set(s['service_name'] for s in spans)),
            'start_time': min(all_start_times),
            'end_time': max(all_end_times)
        }

        return {
            'metadata': trace_metadata,
            'tree': trace_tree,
            'spans': spans  # Include flat list for waterfall view
        }

    @staticmethod
    def calculate_critical_path(spans: List[Dict]) -> List[str]:
        """Calculate critical path through the trace"""
        if not spans:
            return []

        # Sort by duration descending
        sorted_spans = sorted(spans, key=lambda x: x['duration_ns'], reverse=True)

        # Critical path is the longest chain from root to leaf
        span_map = {s['span_id']: s for s in spans}

        def find_longest_path(span_id: str, visited: set) -> List[str]:
            if span_id in visited:
                return []

            visited.add(span_id)
            span = span_map.get(span_id)
            if not span:
                return []

            # Find children
            children = [s for s in spans if s.get('parent_span_id') == span_id]

            if not children:
                return [span_id]

            # Recurse for all children
            longest_child_path = []
            for child in children:
                path = find_longest_path(child['span_id'], visited.copy())
                if len(path) > len(longest_child_path):
                    longest_child_path = path

            return [span_id] + longest_child_path

        # Find root
        root = next((s for s in spans if not s.get('parent_span_id')), spans[0])

        return find_longest_path(root['span_id'], set())

    @staticmethod
    def extract_service_dependencies(spans: List[Dict]) -> List[Dict]:
        """Extract service-to-service dependencies from traces"""
        dependencies = set()

        span_map = {s['span_id']: s for s in spans}

        for span in spans:
            parent_id = span.get('parent_span_id')
            if parent_id and parent_id in span_map:
                parent_span = span_map[parent_id]
                source = parent_span['service_name']
                target = span['service_name']

                if source != target:  # Cross-service call
                    dependencies.add((source, target))

        return [
            {'source': src, 'target': tgt}
            for src, tgt in dependencies
        ]


# ===================================================================
# API ENDPOINTS
# ===================================================================

@app.route('/api/traces/search', methods=['GET'])
@rate_limit(tier='query', max_requests=1000, window_seconds=3600)
@require_auth
def search_traces():
    """Search for traces"""
    try:
        service = request.args.get('service')
        limit = int(request.args.get('limit', 100))
        lookback_minutes = int(request.args.get('lookback', 60))
        min_duration_ms = request.args.get('min_duration')

        # Query OTel collector
        params = {'limit': limit}
        if service:
            params['service'] = service

        response = requests.get(
            f"{OTEL_COLLECTOR_URL}/api/traces",
            params=params,
            timeout=10
        )
        response.raise_for_status()

        traces_data = response.json()
        spans = traces_data.get('traces', [])

        # Filter by duration if specified
        if min_duration_ms:
            min_duration_ns = int(min_duration_ms) * 1_000_000
            spans = [s for s in spans if s['duration_ns'] >= min_duration_ns]

        # Group spans by trace_id
        traces_by_id = {}
        for span in spans:
            trace_id = span['trace_id']
            if trace_id not in traces_by_id:
                traces_by_id[trace_id] = []
            traces_by_id[trace_id].append(span)

        # Build trace summaries
        trace_summaries = []
        for trace_id, trace_spans in traces_by_id.items():
            root_span = next((s for s in trace_spans if not s.get('parent_span_id')), trace_spans[0])

            all_start_times = [s['start_time'] for s in trace_spans]
            all_end_times = [s['end_time'] for s in trace_spans]

            summary = {
                'trace_id': trace_id,
                'root_service': root_span['service_name'],
                'root_operation': root_span['name'],
                'span_count': len(trace_spans),
                'duration_ms': (max(all_end_times) - min(all_start_times)) / 1_000_000,
                'start_time': min(all_start_times),
                'services': list(set(s['service_name'] for s in trace_spans)),
                'has_errors': any(s.get('status_code') == 'ERROR' for s in trace_spans)
            }
            trace_summaries.append(summary)

        # Sort by start time descending
        trace_summaries.sort(key=lambda x: x['start_time'], reverse=True)

        return jsonify({
            'success': True,
            'count': len(trace_summaries),
            'traces': trace_summaries
        }), 200

    except Exception as e:
        logger.error(f"Failed to search traces: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to search traces'
        }), 500


@app.route('/api/traces/<trace_id>', methods=['GET'])
@rate_limit(tier='query', max_requests=1000, window_seconds=3600)
@require_auth
def get_trace_detail(trace_id: str):
    """Get detailed trace data with visualization structure"""
    try:
        # Query OTel collector
        response = requests.get(
            f"{OTEL_COLLECTOR_URL}/api/traces",
            params={'trace_id': trace_id},
            timeout=10
        )
        response.raise_for_status()

        traces_data = response.json()
        spans = traces_data.get('traces', [])

        if not spans:
            return jsonify({
                'success': False,
                'error': 'Trace not found'
            }), 404

        # Build trace tree
        trace_tree = TraceAnalyzer.build_trace_tree(spans)

        # Calculate critical path
        critical_path = TraceAnalyzer.calculate_critical_path(spans)

        # Extract service dependencies
        dependencies = TraceAnalyzer.extract_service_dependencies(spans)

        # Add analysis
        trace_tree['analysis'] = {
            'critical_path': critical_path,
            'service_dependencies': dependencies
        }

        return jsonify({
            'success': True,
            'trace': trace_tree
        }), 200

    except Exception as e:
        logger.error(f"Failed to get trace detail: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve trace'
        }), 500


@app.route('/api/services/topology', methods=['GET'])
@rate_limit(tier='query', max_requests=100, window_seconds=3600)
@require_auth
def get_service_topology():
    """Get service topology graph from recent traces"""
    try:
        lookback_minutes = int(request.args.get('lookback', 60))

        # Query recent traces
        response = requests.get(
            f"{OTEL_COLLECTOR_URL}/api/traces",
            params={'limit': 1000},
            timeout=10
        )
        response.raise_for_status()

        traces_data = response.json()
        spans = traces_data.get('traces', [])

        # Extract all service dependencies
        all_dependencies = TraceAnalyzer.extract_service_dependencies(spans)

        # Count call frequency
        dependency_counts = {}
        for dep in all_dependencies:
            key = (dep['source'], dep['target'])
            dependency_counts[key] = dependency_counts.get(key, 0) + 1

        # Build topology
        nodes = set()
        edges = []

        for (source, target), count in dependency_counts.items():
            nodes.add(source)
            nodes.add(target)
            edges.append({
                'source': source,
                'target': target,
                'call_count': count
            })

        # Calculate node metrics
        node_metrics = {}
        for service in nodes:
            service_spans = [s for s in spans if s['service_name'] == service]

            if service_spans:
                avg_duration = sum(s['duration_ns'] for s in service_spans) / len(service_spans)
                error_count = sum(1 for s in service_spans if s.get('status_code') == 'ERROR')

                node_metrics[service] = {
                    'name': service,
                    'span_count': len(service_spans),
                    'avg_duration_ms': avg_duration / 1_000_000,
                    'error_count': error_count,
                    'error_rate': error_count / len(service_spans) if service_spans else 0
                }

        return jsonify({
            'success': True,
            'topology': {
                'nodes': list(node_metrics.values()),
                'edges': edges
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to build service topology: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to build topology'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'trace_visualizer',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    logger.info("Starting Trace Visualizer on port 8085")
    app.run(
        host='0.0.0.0',
        port=8085,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
