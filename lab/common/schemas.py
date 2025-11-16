"""
Input validation schemas for AI Support Fabric Lab

Uses marshmallow for request validation across all services
"""
import re
from marshmallow import Schema, fields, validate, ValidationError, validates_schema, validates
from typing import Dict, Any
import ipaddress


# ===================================================================
# CUSTOM VALIDATORS
# ===================================================================

class IPAddress(validate.Validator):
    """Validator for IP addresses (IPv4 and IPv6)"""

    def __call__(self, value):
        if not value:
            return value
        try:
            ipaddress.ip_address(value)
            return value
        except ValueError:
            raise ValidationError(f"'{value}' is not a valid IP address")


class SafeString(validate.Validator):
    """Validator for safe strings (alphanumeric + safe special chars)"""

    def __init__(self, allow_spaces=True, allow_dots=True, allow_hyphens=True, allow_underscores=True):
        self.allow_spaces = allow_spaces
        self.allow_dots = allow_dots
        self.allow_hyphens = allow_hyphens
        self.allow_underscores = allow_underscores

    def __call__(self, value):
        if not value:
            return value

        # Build allowed character pattern
        pattern = r'^[a-zA-Z0-9'
        if self.allow_spaces:
            pattern += r'\s'
        if self.allow_dots:
            pattern += r'\.'
        if self.allow_hyphens:
            pattern += r'\-'
        if self.allow_underscores:
            pattern += r'_'
        pattern += r']+$'

        if not re.match(pattern, value):
            raise ValidationError(f"String contains unsafe characters")

        return value


class NoControlChars(validate.Validator):
    """Validator to reject control characters"""

    def __call__(self, value):
        if not value:
            return value

        # Check for control characters (except newline/tab which are normal)
        if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', value):
            raise ValidationError("String contains control characters")

        return value


# ===================================================================
# TELEMETRY SCHEMAS
# ===================================================================

class LogTelemetrySchema(Schema):
    """Schema for log telemetry ingestion"""
    timestamp = fields.Str(required=True)
    service = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            SafeString(allow_spaces=False)
        ]
    )
    level = fields.Str(
        required=True,
        validate=validate.OneOf(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    )
    message = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=10000),
            NoControlChars()
        ]
    )
    request_id = fields.Str(validate=[validate.Length(max=100), SafeString(allow_spaces=False)])
    duration_ms = fields.Int(validate=validate.Range(min=0, max=3600000))
    user = fields.Str(validate=[validate.Length(max=100), SafeString()])
    source_ip = fields.Str(validate=[validate.Length(max=45), IPAddress()])  # IPv6 max length


class MetricTelemetrySchema(Schema):
    """Schema for metric telemetry ingestion"""
    timestamp = fields.Str(required=True)
    service = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            SafeString(allow_spaces=False)
        ]
    )
    metrics = fields.Dict(
        required=True,
        keys=fields.Str(validate=SafeString(allow_spaces=False)),
        values=fields.Number()
    )
    tags = fields.Dict(
        keys=fields.Str(validate=SafeString(allow_spaces=False)),
        values=fields.Str(validate=[validate.Length(max=500), SafeString()])
    )


class ConfigTelemetrySchema(Schema):
    """Schema for configuration change telemetry"""
    timestamp = fields.Str(required=True)
    service = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            SafeString(allow_spaces=False)
        ]
    )
    configuration = fields.Dict(required=True)
    changed_by = fields.Str(validate=[validate.Length(max=100), SafeString()])
    change_reason = fields.Str(validate=[validate.Length(max=500), NoControlChars()])


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


class FindingsQuerySchema(Schema):
    """Schema for querying findings"""
    limit = fields.Int(
        validate=validate.Range(min=1, max=100),
        load_default=20
    )
    severity = fields.Str(
        validate=validate.OneOf(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'])
    )
    detector = fields.Str(validate=SafeString(allow_spaces=False))


class RemediationQuerySchema(Schema):
    """Schema for querying remediation plans"""
    limit = fields.Int(
        validate=validate.Range(min=1, max=100),
        load_default=20
    )
    status = fields.Str(
        validate=validate.OneOf(['pending', 'approved', 'in_progress', 'completed', 'failed'])
    )


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


def validate_query_params(schema_class: type, query_params) -> Dict[str, Any]:
    """
    Validate query parameters from request.args

    Args:
        schema_class: Marshmallow schema class
        query_params: Flask request.args object

    Returns:
        Validated and deserialized data

    Raises:
        ValidationError: If validation fails
    """
    # Convert ImmutableMultiDict to regular dict
    data = {}
    for key, value in query_params.items():
        # Handle type conversion for integers
        if key in ['limit', 'offset']:
            try:
                data[key] = int(value)
            except (ValueError, TypeError):
                raise ValidationError({key: [f"Not a valid integer: {value}"]})
        else:
            data[key] = value

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
