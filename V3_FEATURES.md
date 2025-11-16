# AI Support Fabric Lab v3.0 - Feature Guide

## 🎉 Welcome to v3.0!

This release transforms the AI Support Fabric Lab from an educational demonstration into a **production-ready platform** with enterprise-grade security, observability, and extensibility.

---

## 🔒 Security Enhancements

### 1. API Key Authentication

**Every API endpoint is now protected with API key authentication.**

```python
# Configure API keys in .env
API_KEYS=key1,key2,key3

# Make authenticated requests
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://localhost:8081/api/telemetry/logs',
    json=telemetry_data,
    headers=headers
)
```

**Features:**
- ✅ Configurable via environment variables
- ✅ Multiple API keys supported
- ✅ Health check endpoints remain open
- ✅ Detailed error messages for auth failures
- ✅ Development mode with default key (with warning)

**Security Impact:**
- Prevents unauthorized access to APIs
- Protects against DoS attacks
- Enables access auditing and rate limiting
- Supports multi-tenant deployments

---

### 2. Secure CORS Configuration

**Cross-Origin Resource Sharing is now restricted to allowed origins.**

```python
# Configure allowed origins in .env
ALLOWED_ORIGINS=http://localhost:3000,https://my-domain.com

# CORS configuration in services
CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,  # Restricted!
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Request-ID"]
    }
})
```

**Features:**
- ✅ Origin whitelist from environment
- ✅ Method restrictions
- ✅ Header restrictions
- ✅ Request ID propagation support

**Security Impact:**
- Prevents CSRF attacks
- Protects against malicious websites
- Enforces same-origin policy
- Supports modern security headers

---

### 3. Input Validation

**All API inputs are validated against strict schemas using marshmallow.**

```python
from lab.common.schemas import LogTelemetrySchema, validate_request

# Validation happens automatically
@app.route('/api/telemetry/logs', methods=['POST'])
@require_auth
def ingest_logs():
    try:
        # Validate input against schema
        data = validate_request(LogTelemetrySchema, request.json)

        # Validated data is safe to use
        telemetry_id = store.store_telemetry(data)
        return jsonify({'success': True, 'telemetry_id': telemetry_id}), 201

    except ValidationError as e:
        return jsonify(get_validation_errors(e)), 400
```

**Available Schemas:**
- `LogTelemetrySchema`: Validates log ingestion
- `MetricTelemetrySchema`: Validates metrics
- `ConfigTelemetrySchema`: Validates configuration events
- `TelemetryQuerySchema`: Validates query parameters
- `AnalysisRequestSchema`: Validates analysis requests

**Features:**
- ✅ Type validation (string, int, dict, list)
- ✅ Length validation (min/max)
- ✅ Range validation (numeric ranges)
- ✅ Enum validation (allowed values)
- ✅ Custom validation rules
- ✅ Detailed error messages

**Security Impact:**
- Prevents injection attacks (SQL, command, code)
- Protects against buffer overflows
- Enforces data integrity
- Improves API documentation

---

### 4. Fixed Pickle RCE Vulnerability

**Replaced dangerous `pickle` with secure `joblib` + integrity verification.**

```python
from lab.ml_models.anomaly_detection import MLAnomalyDetector

detector = MLAnomalyDetector()
detector.train(normal_telemetry)

# Save with joblib + SHA-256 signature
detector.save('/data/models/anomaly_detection.joblib')
# Creates: anomaly_detection.joblib + anomaly_detection.joblib.sig

# Load with signature verification
detector.load('/data/models/anomaly_detection.joblib')
# Raises SecurityError if signature doesn't match
```

**Features:**
- ✅ `joblib` instead of `pickle` (safer serialization)
- ✅ SHA-256 signature for integrity
- ✅ Automatic signature generation on save
- ✅ Automatic signature verification on load
- ✅ `SecurityError` on tampering detection

**Security Impact:**
- **CRITICAL**: Prevents Remote Code Execution (RCE)
- Detects file tampering
- Ensures model authenticity
- Prevents supply chain attacks

---

### 5. Command Whitelist System

**Infrastructure commands are whitelisted and require explicit approval.**

```python
# Command whitelist in remediation.py
ALLOWED_COMMANDS = {
    # Read-only diagnostic commands
    'kubectl_top_pods': 'kubectl top pods -n production',
    'kubectl_get_pods': 'kubectl get pods -n production',
    'pg_slow_queries': 'SELECT * FROM pg_stat_statements...',
}

RESTRICTED_COMMANDS = {
    # Dangerous commands requiring approval
    'kubectl_scale': 'kubectl scale deployment/{deployment} --replicas={replicas}',
    'kubectl_apply': 'kubectl apply -f {config_file}',
    'iptables_block': 'iptables -A INPUT -s {ip} -j DROP',
}

# Remediation plans use command references
steps = [
    {
        'action': 'Scale Resources (MANUAL ONLY)',
        'command_ref': 'kubectl_scale',
        'command': get_command('kubectl_scale', deployment='app', replicas='5'),
        'automated': False,  # NEVER automated
        'requires_approval': True  # ALWAYS requires approval
    }
]
```

**Features:**
- ✅ Whitelist of allowed commands
- ✅ Read-only commands for diagnostics
- ✅ Restricted commands for dangerous operations
- ✅ Parameter substitution with validation
- ✅ `automated=False` for all infrastructure commands
- ✅ `requires_approval=True` for destructive operations

**Security Impact:**
- Prevents command injection
- Requires human approval for dangerous operations
- Prevents automated destruction of infrastructure
- Audit trail for command execution

---

## 📊 Observability & Monitoring

### 6. Structured Logging

**Production-ready logging system with JSON and text formats.**

```python
from lab.common.logging_config import setup_logging

# Setup logging for your service
logger = setup_logging(
    'my_service',
    level='INFO',  # or from env: LOG_LEVEL
    log_format='json',  # or 'text'
    log_file='/var/log/my_service.log'  # optional
)

# Use logger throughout your code
logger.info("Request started", extra={'request_id': 'req-123'})
logger.error("Database connection failed", extra={'duration_ms': 5000})
logger.exception("An error occurred")  # Includes stack trace
```

**JSON Log Output:**
```json
{
    "timestamp": "2025-01-16T10:30:00.123Z",
    "level": "INFO",
    "logger": "agentic_ai.engine",
    "message": "Detection complete: 3 findings identified",
    "module": "engine",
    "function": "run_detection",
    "line": 79,
    "request_id": "req-123",
    "duration_ms": 1234
}
```

**Features:**
- ✅ JSON format for machine parsing
- ✅ Text format for human reading
- ✅ Request ID tracking
- ✅ Automatic timestamps (UTC)
- ✅ Module/function/line tracking
- ✅ Exception stack traces
- ✅ Rotating file handlers (10MB per file, 5 backups)
- ✅ Configurable log levels

**Benefits:**
- Easy integration with log aggregation (ELK, Splunk, Datadog)
- Request tracing across services
- Production debugging
- Performance monitoring
- Security audit trails

---

## 🏗️ Architecture Improvements

### 7. Proper Package Structure

**All services are now proper Python packages with clean imports.**

```
lab/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── auth.py
│   ├── schemas.py
│   └── logging_config.py
├── agentic_ai/
│   ├── __init__.py
│   └── src/
│       ├── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── finding.py
│       ├── api.py
│       ├── engine.py
│       └── detectors.py
└── telemetry_collector/
    ├── __init__.py
    └── src/
        ├── __init__.py
        ├── app.py
        └── storage/
            ├── __init__.py
            └── store.py
```

**Import Examples:**
```python
# Before (v2.0)
from detectors import Finding  # ModuleNotFoundError!

# After (v3.0)
from .models import Finding  # Clean and works!

# Cross-service imports
from lab.common.auth import require_auth
from lab.common.schemas import LogTelemetrySchema
```

**Features:**
- ✅ All `__init__.py` files created
- ✅ No more `ModuleNotFoundError`
- ✅ Clean import paths
- ✅ Centralized shared code in `lab/common/`
- ✅ No `sys.path` manipulation needed

**Benefits:**
- Easier to maintain
- Better IDE support
- Clearer dependencies
- Follows Python best practices

---

### 8. Centralized Common Module

**Shared code is now in `lab/common/` for reuse across services.**

```
lab/common/
├── auth.py           # Authentication & authorization
├── schemas.py        # Input validation schemas
└── logging_config.py # Logging configuration
```

**Usage:**
```python
# All services can use common code
from lab.common.auth import require_auth, setup_auth_error_handlers
from lab.common.schemas import validate_request, LogTelemetrySchema
from lab.common.logging_config import setup_logging

# Apply to your service
app = Flask(__name__)
setup_auth_error_handlers(app)
logger = setup_logging('my_service')

@app.route('/api/endpoint')
@require_auth
def my_endpoint():
    data = validate_request(LogTelemetrySchema, request.json)
    logger.info("Request processed", extra={'data': data})
    return jsonify({'success': True})
```

**Benefits:**
- Code reuse across services
- Consistent behavior
- Single source of truth
- Easier to maintain and update

---

## 📦 Developer Experience

### 9. Comprehensive Environment Configuration

**`.env.example` with 100+ configuration options.**

```bash
# .env.example structure

# SECURITY - API Authentication
API_KEYS=dev-key-DO-NOT-USE-IN-PRODUCTION,key2

# SECURITY - CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# SERVICE CONFIGURATION
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# DATABASE & STORAGE
TELEMETRY_STORAGE_PATH=/data/telemetry.db

# LLM PROVIDERS
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...
LLM_PROVIDER=anthropic

# OBSERVABILITY
PROMETHEUS_METRICS_ENABLED=true

# MULTI-TENANCY (v3.0+ feature)
MULTI_TENANCY_ENABLED=false
DEFAULT_TENANT_ID=default

# And many more...
```

**Features:**
- ✅ 100+ configuration options documented
- ✅ Security settings (API keys, CORS, HTTPS)
- ✅ Service configuration (ports, URLs, debug)
- ✅ LLM provider settings
- ✅ Database configuration
- ✅ Feature flags
- ✅ Inline documentation and examples
- ✅ Security warnings for production

**Benefits:**
- Easy configuration management
- Environment-specific settings
- Security best practices built-in
- No hardcoded secrets

---

### 10. Dependency Management

**`requirements.txt` with all dependencies clearly documented.**

```txt
# Core dependencies
Flask==3.0.0
flask-cors==4.0.0
marshmallow==3.20.1

# ML & Data Science
scikit-learn==1.3.2
numpy==1.26.2
joblib==1.3.2

# LLM Integrations
anthropic==0.8.1
openai==1.6.1

# Development & Testing
pytest==7.4.3
pytest-cov==4.1.0

# Optional production dependencies (commented)
# flask-limiter==3.5.0
# prometheus-flask-exporter==0.22.4
# gunicorn==21.2.0
```

**Installation:**
```bash
# Install all dependencies
pip install -r requirements.txt

# Install with optional production deps
# Uncomment in requirements.txt, then:
pip install -r requirements.txt
```

**Benefits:**
- Reproducible environments
- Version pinning for stability
- Clear dependency documentation
- Easy onboarding for new developers

---

## 🚀 Getting Started with v3.0

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repo>
   cd Secure-AI-Support-Fabric
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Generate API Keys**
   ```bash
   # Generate strong API keys
   openssl rand -hex 32
   # Add to .env: API_KEYS=<generated-key>
   ```

5. **Start Services**
   ```bash
   docker-compose up
   ```

6. **Test Authentication**
   ```bash
   # This will fail (no API key)
   curl http://localhost:8081/api/telemetry/stats

   # This will succeed
   curl -H "X-API-Key: your-key-here" \
        http://localhost:8081/api/telemetry/stats
   ```

---

## 📖 Documentation

### New Documentation Files

- **CHANGELOG.md**: Complete version history
- **V3_FEATURES.md**: This file - feature guide
- **REVIEW_AND_V3_ROADMAP.md**: Code review and roadmap
- **ISSUES_SUMMARY.md**: Critical issues summary
- **.env.example**: Environment configuration template
- **requirements.txt**: Python dependencies

---

## 🔄 Migration from v2.0

See **CHANGELOG.md** for detailed migration steps.

**Key Changes:**
1. Add `X-API-Key` header to all API requests
2. Configure `API_KEYS` and `ALLOWED_ORIGINS` in `.env`
3. Update imports (relative imports now required)
4. Retrain ML models (pickle → joblib)
5. Install new dependencies from `requirements.txt`

---

## 🎯 What's Next?

v3.0 is production-ready for educational and small-scale deployments. Future versions will add:

**v3.1 - v3.3**: Production hardening, observability, advanced features
**v4.0**: Enterprise edition with TimescaleDB, Kubernetes, multi-region

See **CHANGELOG.md** for the complete roadmap.

---

## 🙏 Feedback & Contributions

Found a bug? Have a feature request? Open an issue!

Want to contribute? Pull requests welcome!

---

**Happy Detecting! 🔍🤖**
