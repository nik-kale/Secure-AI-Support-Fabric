"""
Input validation schemas for AI Support Fabric Lab

Uses marshmallow for request validation across all services
"""
from marshmallow import Schema, fields, validate, ValidationError, validates_schema
from typing import Dict, Any


# ===================================================================
# TELEMETRY SCHEMAS
# ===================================================================

class LogTelemetrySchema(Schema):
    """Schema for log telemetry ingestion"""
    timestamp = fields.Str(required=True)
    service = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    level = fields.Str(
        required=True,
        validate=validate.OneOf(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    )
    message = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=10000)
    )
    request_id = fields.Str(validate=validate.Length(max=100))
    duration_ms = fields.Int(validate=validate.Range(min=0, max=3600000))
    user = fields.Str(validate=validate.Length(max=100))
    source_ip = fields.Str(validate=validate.Length(max=45))  # IPv6 max length


class MetricTelemetrySchema(Schema):
    """Schema for metric telemetry ingestion"""
    timestamp = fields.Str(required=True)
    service = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    metrics = fields.Dict(
        required=True,
        keys=fields.Str(),
        values=fields.Number()
    )
    tags = fields.Dict(
        keys=fields.Str(),
        values=fields.Str()
    )


class ConfigTelemetrySchema(Schema):
    """Schema for configuration change telemetry"""
    timestamp = fields.Str(required=True)
    service = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    configuration = fields.Dict(required=True)
    changed_by = fields.Str(validate=validate.Length(max=100))
    change_reason = fields.Str(validate=validate.Length(max=500))


# ===================================================================
# QUERY SCHEMAS
# ===================================================================

class TelemetryQuerySchema(Schema):
    """Schema for querying telemetry"""
    type = fields.Str(
        validate=validate.OneOf(['log', 'metric', 'config'])
    )
    limit = fields.Int(
        validate=validate.Range(min=1, max=1000),
        load_default=100
    )
    since = fields.Str()  # ISO timestamp
    until = fields.Str()  # ISO timestamp

    @validates_schema
    def validate_time_range(self, data, **kwargs):
        """Ensure since < until if both provided"""
        if 'since' in data and 'until' in data:
            if data['since'] >= data['until']:
                raise ValidationError('since must be before until')


# ===================================================================
# ANALYSIS SCHEMAS
# ===================================================================

class AnalysisRequestSchema(Schema):
    """Schema for analysis requests"""
    telemetry_types = fields.List(
        fields.Str(validate=validate.OneOf(['log', 'metric', 'config'])),
        load_default=['log', 'metric', 'config']
    )
    limit = fields.Int(
        validate=validate.Range(min=1, max=1000),
        load_default=200
    )
    detectors = fields.List(
        fields.Str(),
        load_default=None  # None = all detectors
    )


class RemediationRequestSchema(Schema):
    """Schema for remediation plan generation"""
    finding_ids = fields.List(
        fields.Str(),
        validate=validate.Length(min=1, max=100)
    )


# ===================================================================
# VALIDATION UTILITIES
# ===================================================================

def validate_request(schema_class: type, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate request data against schema

    Args:
        schema_class: Marshmallow schema class
        data: Data to validate

    Returns:
        Validated and deserialized data

    Raises:
        ValidationError: If validation fails
    """
    schema = schema_class()
    return schema.load(data)


def get_validation_errors(error: ValidationError) -> Dict[str, Any]:
    """
    Format validation errors for API response

    Args:
        error: ValidationError exception

    Returns:
        Formatted error dict
    """
    return {
        'error': 'Validation failed',
        'details': error.messages,
        'valid': False
    }


# ===================================================================
# EXAMPLE USAGE
# ===================================================================

if __name__ == '__main__':
    # Test log telemetry validation
    valid_log = {
        'timestamp': '2024-01-15T10:30:00Z',
        'service': 'api-gateway',
        'level': 'ERROR',
        'message': 'Failed to connect to database',
        'duration_ms': 1500
    }

    try:
        result = validate_request(LogTelemetrySchema, valid_log)
        print(f"✓ Valid log telemetry: {result}")
    except ValidationError as e:
        print(f"✗ Validation error: {e.messages}")

    # Test invalid log
    invalid_log = {
        'timestamp': '2024-01-15T10:30:00Z',
        'service': 'api-gateway',
        'level': 'INVALID_LEVEL',  # Invalid level
        'message': 'x' * 20000  # Too long
    }

    try:
        result = validate_request(LogTelemetrySchema, invalid_log)
        print(f"✓ Valid: {result}")
    except ValidationError as e:
        print(f"✗ Expected validation error: {e.messages}")
