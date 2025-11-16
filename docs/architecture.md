# AI Support Fabric Lab - Architecture

## Overview

The AI Support Fabric Lab is a hands-on educational environment that demonstrates how AI-driven proactive support works using synthetic telemetry, agentic detection, and guided remediation.

## High-Level Architecture

```
┌─────────────────┐
│  External Test  │
│    Services     │
└────────┬────────┘
         │ telemetry
         ▼
┌─────────────────────────────────────────────────────────┐
│                    Gateway (Port 8080)                   │
│  - Request routing                                       │
│  - Context propagation (X-Request-ID, tracing)          │
│  - Unified API                                           │
└──────┬─────────────────────────────────────────┬────────┘
       │                                          │
       ▼                                          ▼
┌──────────────────┐                   ┌──────────────────┐
│  Telemetry       │                   │  Agentic AI      │
│  Collector       │◄──────────────────│  Engine          │
│  (Port 8081)     │   fetch telemetry │  (Port 8082)     │
│                  │                   │                  │
│  - Ingest logs   │                   │  - Detectors     │
│  - Ingest metrics│                   │  - Remediation   │
│  - Ingest config │                   │  - Findings      │
│  - SQLite store  │                   │                  │
└──────────────────┘                   └──────────────────┘
       ▲                                          │
       │                                          │
       │                                          ▼
       │                               ┌──────────────────┐
       │                               │  UI Dashboard    │
       └───────────────────────────────│  (Port 3000)     │
                                       │                  │
                                       │  - Visualize     │
                                       │  - Monitor       │
                                       │  - Alert         │
                                       └──────────────────┘
```

## Components

### 1. Gateway Service

**Purpose**: Central entry point and request router

**Responsibilities**:
- Route requests to appropriate backend services
- Add context headers for distributed tracing
- Provide unified API for external clients
- Aggregate health status from all services

**Technology Stack**:
- Python 3.11
- Flask web framework
- Docker containerized

**API Endpoints**:
- `GET /health` - Aggregated health check
- `/api/telemetry/*` - Proxy to telemetry collector
- `/api/ai/*` - Proxy to agentic AI
- `POST /api/run-analysis` - Trigger analysis cycle
- `GET /api/status` - Overall system status

**Context Propagation**:
- `X-Request-ID`: Unique request identifier (generated if not present)
- `X-Gateway-Timestamp`: Request timestamp

### 2. Telemetry Collector Service

**Purpose**: Ingest and store synthetic telemetry data

**Responsibilities**:
- Accept telemetry via REST API (logs, metrics, configs)
- Validate and enrich telemetry data
- Store in SQLite database
- Provide query API for retrieval

**Technology Stack**:
- Python 3.11
- Flask web framework
- SQLite database
- Docker containerized

**Data Model**:

```sql
CREATE TABLE telemetry (
    id TEXT PRIMARY KEY,
    telemetry_type TEXT NOT NULL,  -- 'log', 'metric', 'config'
    ingested_at TEXT NOT NULL,      -- ISO 8601 timestamp
    data TEXT NOT NULL,              -- JSON blob
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**API Endpoints**:
- `POST /api/telemetry/logs` - Ingest log entries
- `POST /api/telemetry/metrics` - Ingest metrics
- `POST /api/telemetry/config` - Ingest config events
- `GET /api/telemetry/query` - Query telemetry
- `GET /api/telemetry/stats` - Get statistics

**Generators**:
The service includes synthetic telemetry generators:
- `LogGenerator`: Generate realistic log entries
- `MetricGenerator`: Generate system metrics
- `ConfigGenerator`: Generate config events
- `ScenarioGenerator`: Generate complete scenarios

### 3. Agentic AI Engine

**Purpose**: Analyze telemetry and generate findings with remediation plans

**Responsibilities**:
- Fetch telemetry from collector
- Run detection algorithms
- Generate findings for anomalies
- Create remediation plans
- Cache results

**Technology Stack**:
- Python 3.11
- Flask web framework
- Rule-based detection (no actual LLM in this lab version)
- Docker containerized

**Detection Pipeline**:

```
Telemetry → Detector 1 (Latency)  → Finding 1
         ├→ Detector 2 (Config)   → Finding 2
         └→ Detector 3 (Auth)     → Finding 3
                                       ↓
                            Remediation Engine
                                       ↓
                            Remediation Plans
```

**Detectors**:

1. **LatencySpikeDetector**
   - Monitors request duration
   - Threshold: 1000ms
   - Minimum occurrences: 3
   - Severity: HIGH

2. **ConfigDriftDetector**
   - Compares against baseline configuration
   - Detects security-critical changes
   - Severity: CRITICAL (auth/TLS), MEDIUM (others)

3. **AuthFailureDetector**
   - Monitors authentication failures
   - Threshold: 10 failures
   - Groups by user and IP
   - Severity: HIGH

**API Endpoints**:
- `POST /api/analyze` - Run full analysis cycle
- `POST /api/detect` - Detection only
- `POST /api/remediate` - Generate remediation plans
- `GET /api/findings` - Get findings
- `GET /api/remediation` - Get remediation plans

### 4. UI Dashboard

**Purpose**: Web-based visualization and monitoring

**Responsibilities**:
- Display system health
- Show telemetry statistics
- Present findings
- Display remediation plans
- Auto-refresh data

**Technology Stack**:
- Python 3.11 + Flask backend
- HTML/CSS/JavaScript frontend
- Single-page application
- Docker containerized

**Features**:
- Real-time health monitoring
- Finding severity visualization
- Remediation plan presentation
- Auto-refresh every 30 seconds
- Responsive design

## Data Flow

### Telemetry Ingestion Flow

```
1. External Service → Gateway → Telemetry Collector
2. Telemetry Collector validates data
3. Data enriched with metadata (timestamp, type)
4. Stored in SQLite database
5. Response returned to client
```

### Analysis Flow

```
1. Trigger (manual via API or automated)
2. AI Engine fetches recent telemetry
3. Each detector analyzes telemetry
4. Findings generated for anomalies
5. Remediation plans created for findings
6. Results cached in memory
7. Available via API
```

### Remediation Flow

```
1. Finding detected
2. Remediation Engine routes to appropriate strategy
3. Strategy generates step-by-step plan
4. Steps include:
   - Investigation commands
   - Mitigation actions
   - Verification steps
   - Risk flags (requires_approval)
5. Plan returned to user/dashboard
```

## Security Considerations

### Educational Environment Only

**This lab is designed for education and research only.**

- No real credentials or production data
- Isolated Docker network
- No external network access required
- Safe to run on local development machines

### Best Practices Demonstrated

1. **No Hardcoded Secrets**: All config via environment variables
2. **Minimal Attack Surface**: Services only expose required ports
3. **Input Validation**: API endpoints validate inputs
4. **Least Privilege**: Containers run as non-root (in production)
5. **Audit Trail**: All telemetry includes timestamps and sources

## Scalability Considerations

### Current Lab (Single Machine)

- SQLite for simplicity
- In-memory caching
- No horizontal scaling
- Suitable for demo/education

### Production Evolution Path

To productionize this architecture:

1. **Storage**: Replace SQLite with PostgreSQL/TimescaleDB
2. **Message Queue**: Add Kafka/RabbitMQ for async processing
3. **Cache**: Add Redis for distributed caching
4. **Scaling**: Containerize with Kubernetes
5. **Monitoring**: Add Prometheus/Grafana
6. **AI**: Replace rule-based with actual LLM integration
7. **Authentication**: Add OAuth2/JWT
8. **Rate Limiting**: Add API rate limiting

## Extension Points

The lab is designed to be extended:

### Add New Detectors

1. Create detector class in `lab/agentic_ai/src/detectors.py`
2. Implement `analyze(telemetry)` method
3. Return `Finding` object
4. Register in `AnomalyDetectorEngine`

### Add New Remediation Strategies

1. Create strategy method in `lab/agentic_ai/src/remediation.py`
2. Return `RemediationPlan` with steps
3. Route from `generate_plan()`

### Add New Telemetry Types

1. Add endpoint in `lab/telemetry_collector/src/app.py`
2. Create generator in `generators/`
3. Update database queries if needed

### Integrate Real LLM

Replace rule-based logic in detectors/remediation with LLM calls:

```python
# Example: Replace rule-based detection with LLM
def analyze_with_llm(self, telemetry):
    prompt = f"Analyze this telemetry: {telemetry}"
    response = llm_client.complete(prompt)
    return parse_llm_finding(response)
```

## Deployment

### Local Development

```bash
docker-compose up --build
```

### Production Considerations

- Use production WSGI server (gunicorn, uWSGI)
- Enable TLS/HTTPS
- Set up proper logging
- Configure resource limits
- Implement backup strategy
- Add monitoring/alerting

## Performance Characteristics

### Expected Performance (Lab)

- Telemetry ingestion: 100+ requests/sec
- Detection latency: < 5 seconds for 1000 entries
- API response time: < 200ms (p95)
- Storage: Grows linearly with telemetry volume

### Optimization Opportunities

- Add database indexes for common queries
- Implement pagination for large result sets
- Cache expensive detector computations
- Batch telemetry ingestion
- Use connection pooling

## Monitoring

### Health Checks

All services implement `/health` endpoint:

```json
{
  "status": "healthy",
  "service": "service_name",
  "timestamp": "2025-01-15T10:00:00Z"
}
```

Gateway aggregates health:

```json
{
  "status": "healthy",
  "services": {
    "telemetry_collector": "healthy",
    "agentic_ai": "healthy"
  }
}
```

### Metrics

Available via telemetry stats endpoint:

- Total telemetry count
- Count by type
- Latest ingestion timestamp

## Future Enhancements

1. **Real LLM Integration**: Replace rules with Claude/GPT
2. **Multi-Tenancy**: Support multiple isolated environments
3. **Advanced Analytics**: ML-based anomaly detection
4. **Automated Remediation**: Execute safe remediation automatically
5. **Feedback Loop**: Learn from remediation outcomes
6. **Alert Routing**: Integrate with PagerDuty, Slack, etc.
7. **Compliance**: Add SOC2, HIPAA compliance checks
8. **Chaos Engineering**: Inject failures for testing
