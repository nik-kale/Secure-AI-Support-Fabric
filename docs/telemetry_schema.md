# Telemetry Schema Documentation

## Overview

The AI Support Fabric Lab uses three primary telemetry types:

1. **Logs**: Application log entries
2. **Metrics**: System and application metrics
3. **Config**: Configuration change events

All telemetry is stored as JSON and includes common metadata fields.

## Common Metadata

All telemetry entries automatically receive these fields upon ingestion:

```json
{
  "ingested_at": "2025-01-15T10:30:00.123456Z",
  "telemetry_type": "log|metric|config",
  "telemetry_id": "uuid-generated-by-collector"
}
```

## Log Telemetry

### Purpose
Capture application events, errors, and operational information.

### Schema

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "string",
  "level": "DEBUG|INFO|WARNING|ERROR|CRITICAL",
  "message": "string",
  "request_id": "string (optional)",
  "duration_ms": "number (optional)",
  "user_id": "string (optional)",
  "user": "string (optional)",
  "endpoint": "string (optional)",
  "source_ip": "string (optional)",
  "reason": "string (optional)",
  "expected_duration_ms": "number (optional)"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 string | Yes | When the log event occurred |
| `service` | string | Yes | Service name that generated the log |
| `level` | enum | Yes | Log severity level |
| `message` | string | Yes | Human-readable log message |
| `request_id` | string | No | Unique identifier for request tracing |
| `duration_ms` | number | No | Request/operation duration in milliseconds |
| `user_id` | string | No | Identifier of user associated with event |
| `user` | string | No | Username (for auth events) |
| `endpoint` | string | No | API endpoint being accessed |
| `source_ip` | string | No | IP address of request origin |
| `reason` | string | No | Reason for event (e.g., failure reason) |
| `expected_duration_ms` | number | No | Expected duration for comparison |

### Examples

#### Normal Request Log

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "api-service",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "req-1234",
  "duration_ms": 150,
  "user_id": "user_001",
  "endpoint": "/api/data"
}
```

#### Slow Request Warning

```json
{
  "timestamp": "2025-01-15T10:31:00Z",
  "service": "api-service",
  "level": "WARNING",
  "message": "Request took longer than expected",
  "request_id": "req-1235",
  "duration_ms": 5500,
  "expected_duration_ms": 200,
  "endpoint": "/api/slow-query"
}
```

#### Authentication Failure

```json
{
  "timestamp": "2025-01-15T10:32:00Z",
  "service": "auth-service",
  "level": "ERROR",
  "message": "Authentication failed",
  "request_id": "req-1236",
  "user": "john_doe",
  "reason": "Invalid credentials",
  "source_ip": "192.168.1.100"
}
```

## Metric Telemetry

### Purpose
Capture system resource utilization and application performance metrics.

### Schema

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "string",
  "metrics": {
    "cpu_percent": "number (0-100)",
    "memory_percent": "number (0-100)",
    "request_rate": "number (requests/sec)",
    "error_rate": "number (percentage)",
    "avg_latency_ms": "number (milliseconds)",
    "custom_metric_name": "number"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 string | Yes | When metrics were collected |
| `service` | string | Yes | Service name being measured |
| `metrics` | object | Yes | Key-value pairs of metric measurements |
| `metrics.cpu_percent` | number | No | CPU utilization percentage (0-100) |
| `metrics.memory_percent` | number | No | Memory utilization percentage (0-100) |
| `metrics.request_rate` | number | No | Requests per second |
| `metrics.error_rate` | number | No | Error percentage |
| `metrics.avg_latency_ms` | number | No | Average latency in milliseconds |

### Examples

#### Normal Metrics

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "api-service",
  "metrics": {
    "cpu_percent": 35.5,
    "memory_percent": 42.3,
    "request_rate": 120,
    "error_rate": 0.5,
    "avg_latency_ms": 85
  }
}
```

#### High Load Metrics

```json
{
  "timestamp": "2025-01-15T10:31:00Z",
  "service": "api-service",
  "metrics": {
    "cpu_percent": 92.0,
    "memory_percent": 78.5,
    "request_rate": 450,
    "error_rate": 12.3,
    "avg_latency_ms": 3500
  }
}
```

## Configuration Telemetry

### Purpose
Track configuration changes and detect drift from baselines.

### Schema

```json
{
  "timestamp": "2025-01-15T10:00:00Z",
  "service": "string",
  "config_version": "string",
  "configuration": {
    "debug_mode": "boolean",
    "log_level": "string",
    "max_connections": "number",
    "timeout_seconds": "number",
    "rate_limit": "number",
    "enable_auth": "boolean",
    "tls_enabled": "boolean",
    "custom_setting": "any"
  },
  "changed_by": "string",
  "change_reason": "string"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 string | Yes | When configuration changed |
| `service` | string | Yes | Service name |
| `config_version` | string | Yes | Version identifier for config |
| `configuration` | object | Yes | Complete or partial config snapshot |
| `changed_by` | string | Yes | Who/what made the change |
| `change_reason` | string | No | Reason for the change |

### Baseline Configuration

The default baseline configuration for drift detection:

```json
{
  "debug_mode": false,
  "log_level": "INFO",
  "max_connections": 100,
  "timeout_seconds": 30,
  "rate_limit": 1000,
  "enable_auth": true,
  "tls_enabled": true
}
```

### Examples

#### Normal Configuration

```json
{
  "timestamp": "2025-01-15T10:00:00Z",
  "service": "api-service",
  "config_version": "1.0.0",
  "configuration": {
    "debug_mode": false,
    "log_level": "INFO",
    "max_connections": 100,
    "timeout_seconds": 30,
    "rate_limit": 1000,
    "enable_auth": true,
    "tls_enabled": true
  },
  "changed_by": "admin",
  "change_reason": "Initial deployment"
}
```

#### Configuration Drift

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "api-service",
  "config_version": "1.0.1-drift",
  "configuration": {
    "debug_mode": true,
    "log_level": "DEBUG",
    "max_connections": 100,
    "timeout_seconds": 30,
    "rate_limit": 1000,
    "enable_auth": false,
    "tls_enabled": false
  },
  "changed_by": "unknown",
  "change_reason": "Unauthorized change detected"
}
```

## API Endpoints

### Ingest Telemetry

#### Ingest Logs

```http
POST /api/telemetry/logs
Content-Type: application/json

{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "my-service",
  "level": "INFO",
  "message": "Example log"
}
```

**Response:**
```json
{
  "success": true,
  "telemetry_id": "uuid",
  "message": "Log telemetry ingested successfully"
}
```

#### Ingest Metrics

```http
POST /api/telemetry/metrics
Content-Type: application/json

{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "my-service",
  "metrics": {
    "cpu_percent": 45.5
  }
}
```

**Response:**
```json
{
  "success": true,
  "telemetry_id": "uuid",
  "message": "Metric telemetry ingested successfully"
}
```

#### Ingest Config

```http
POST /api/telemetry/config
Content-Type: application/json

{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "my-service",
  "config_version": "1.0.0",
  "configuration": {
    "debug_mode": false
  },
  "changed_by": "admin",
  "change_reason": "Production deployment"
}
```

**Response:**
```json
{
  "success": true,
  "telemetry_id": "uuid",
  "message": "Config telemetry ingested successfully"
}
```

### Query Telemetry

```http
GET /api/telemetry/query?type=log&limit=100&since=2025-01-15T00:00:00Z
```

**Query Parameters:**
- `type` (optional): Filter by type (`log`, `metric`, `config`)
- `limit` (optional): Number of results (default: 100)
- `since` (optional): ISO 8601 timestamp for time filtering

**Response:**
```json
{
  "success": true,
  "count": 2,
  "telemetry": [
    {
      "id": "uuid-1",
      "telemetry_type": "log",
      "ingested_at": "2025-01-15T10:30:00Z",
      "data": { ... }
    }
  ]
}
```

### Get Statistics

```http
GET /api/telemetry/stats
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_count": 1234,
    "count_by_type": {
      "log": 1000,
      "metric": 200,
      "config": 34
    },
    "latest_telemetry": "2025-01-15T10:30:00Z"
  }
}
```

## Best Practices

### Timestamps

- Always use ISO 8601 format with UTC timezone
- Include milliseconds for precision: `2025-01-15T10:30:00.123Z`
- Be consistent across all telemetry types

### Service Names

- Use lowercase with hyphens: `api-service`, `auth-service`
- Keep names consistent across telemetry types
- Use descriptive names that indicate function

### Log Levels

Use appropriate severity:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages, potential issues
- `ERROR`: Error events, functionality affected
- `CRITICAL`: Critical errors, system unstable

### Request IDs

- Use UUIDs or other unique identifiers
- Propagate through entire request chain
- Include in all related logs for tracing

### Metrics Collection

- Collect at regular intervals (e.g., every 30 seconds)
- Use consistent metric names
- Include timestamp of collection
- Avoid excessive cardinality

### Configuration Changes

- Always log who made the change
- Include reason/justification
- Capture complete config snapshot
- Version all configurations

## Extending the Schema

To add custom fields:

1. Add fields to your telemetry JSON
2. Update generators if using synthetic data
3. Modify detectors to use new fields
4. Document in this schema file

Example custom log field:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "service": "payment-service",
  "level": "INFO",
  "message": "Payment processed",
  "custom_transaction_id": "txn-12345",
  "custom_amount_usd": 99.99
}
```

## Validation

The collector performs basic validation:

- Required fields must be present
- Timestamps must be valid ISO 8601
- Numeric values must be numbers
- Enum fields must match allowed values

Invalid telemetry is rejected with HTTP 400.

## Storage

Telemetry is stored in SQLite with this schema:

```sql
CREATE TABLE telemetry (
    id TEXT PRIMARY KEY,
    telemetry_type TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    data TEXT NOT NULL,  -- JSON blob
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The `data` field contains the complete telemetry JSON for flexible querying.
