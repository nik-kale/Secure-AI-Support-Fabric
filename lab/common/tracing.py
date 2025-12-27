"""
OpenTelemetry Tracing Configuration
"""
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def setup_tracing(service_name: str, app=None):
    """
    Configure OpenTelemetry tracing for a service.
    
    Args:
        service_name: Name of the service (e.g., 'gateway', 'agentic-ai')
        app: Flask application instance (optional)
    """
    # Check if tracing is enabled
    if os.getenv('ENABLE_TRACING', 'false').lower() != 'true':
        return

    # OTLP Collector Endpoint
    otlp_endpoint = os.getenv('OTLP_ENDPOINT', 'http://otel-collector:4317')

    # Create Resource
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": os.getenv('FLASK_ENV', 'development')
    })

    # Setup Tracer Provider
    provider = TracerProvider(resource=resource)
    
    # Setup Exporter
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    
    # Setup Processor
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    # Set Global Tracer Provider
    trace.set_tracer_provider(provider)

    # Instrument Requests
    RequestsInstrumentor().instrument()

    # Instrument Flask
    if app:
        FlaskInstrumentor().instrument_app(app)
        
    return trace.get_tracer(service_name)

