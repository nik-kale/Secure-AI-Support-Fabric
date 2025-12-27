"""
Prometheus Metrics Configuration
"""
import os
from prometheus_flask_exporter import PrometheusMetrics
from flask import Flask

def setup_metrics(app: Flask):
    """
    Configure Prometheus metrics for a Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        PrometheusMetrics instance
    """
    # Check if metrics are enabled
    if os.getenv('ENABLE_METRICS', 'true').lower() != 'true':
        return None

    metrics = PrometheusMetrics(app)
    
    # Add static information
    metrics.info('app_info', 'Application info', version='1.0.0')
    
    return metrics

