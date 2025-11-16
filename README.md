# ai-support-fabric-lab

**A local lab to explore AI-driven proactive support using synthetic telemetry, agentic detection, and guided remediation.**

## 🆕 What's New in v2.0 - Next Level Edition

**Major upgrades and new features:**

- ✅ **Comprehensive Testing Suite** - 75%+ test coverage, automated CI/CD
- ✅ **Real LLM Integration** - Anthropic Claude, OpenAI GPT, Local models
- ✅ **Plugin System** - Hot-loadable custom detectors
- ✅ **ML Anomaly Detection** - Sklearn-based unsupervised learning
- ✅ **Python SDK** - Fluent API for easy integration
- ✅ **GitHub Actions CI/CD** - Automated testing and security scanning

**📖 [See full improvements →](IMPROVEMENTS.md)** | **🚀 [Quick Start Guide →](QUICKSTART.md)**

---

## 1. Motivation

### Why AI-Support Fabric?

Modern software systems generate massive amounts of telemetry data - logs, metrics, traces, and configuration events. Traditional reactive support models wait for users to report issues, leading to:

- **Delayed incident response**: Problems escalate before detection
- **Blind spots**: Issues go unnoticed until critical
- **Configuration drift**: Security settings change without detection
- **Alert fatigue**: Too many false positives, missed real issues
- **Manual remediation**: Time-consuming, error-prone fixes

### What This Lab Demonstrates

This lab showcases a proactive AI-driven support fabric that:

1. **Ingests synthetic telemetry** from microservices (logs, metrics, config events)
2. **Detects anomalies** using agentic AI logic (latency spikes, config drift, security issues)
3. **Generates findings** with severity, evidence, and context
4. **Suggests remediation** with step-by-step guided fixes
5. **Optionally automates** low-risk mitigations with human oversight

**Key insight**: By continuously analyzing telemetry with AI, you can detect and fix issues before they impact users.

---

## 2. Lab Architecture

### High-Level Overview

```
[service under test] --> [telemetry_collector] --> [agentic_ai]
                                        ^             |
                                        |             v
                                      [gateway] <-- [ui_dash]
```

### Components and Responsibilities

| Component | Port | Responsibility |
|-----------|------|----------------|
| **telemetry_collector** | 8081 | Ingest synthetic logs/metrics/config events, store in SQLite |
| **agentic_ai** | 8082 | Run detection rules, generate findings and remediation plans |
| **gateway** | 8080 | API routing, context propagation (request IDs, tracing) |
| **ui_dash** | 3000 | Web UI for visualizing anomalies and remediation suggestions |

### Data Flow

```
1. Telemetry ingestion → Gateway → Collector → SQLite storage
2. Analysis trigger → AI Engine → Fetch telemetry → Run detectors
3. Findings + Remediation → Cache → API → Dashboard
```

---

## 3. Features

### Synthetic Telemetry Scenarios

Three pre-built scenarios demonstrate different operational issues:

1. **scenario_latency_spike**
   - Simulates slow requests (5-15 seconds)
   - High CPU usage metrics
   - **Detection**: LatencySpikeDetector (threshold: 1000ms, min: 3 occurrences)
   - **Remediation**: Investigate load, check database, scale resources

2. **scenario_config_drift**
   - Unauthorized config changes (debug mode enabled, auth disabled)
   - **Detection**: ConfigDriftDetector (compares against baseline)
   - **Remediation**: Verify authorization, assess security impact, rollback if needed

3. **scenario_auth_error_storm**
   - Multiple failed login attempts (potential brute-force attack)
   - **Detection**: AuthFailureDetector (threshold: 10 failures)
   - **Remediation**: Rate limiting, IP blocking, MFA enforcement

### Agentic Detection Pipeline

The AI engine uses multiple specialized "agents" (detectors):

- **LatencySpikeDetector**: Identifies performance degradation
- **ConfigDriftDetector**: Catches unauthorized configuration changes
- **AuthFailureDetector**: Detects potential security attacks

Each detector:
- Analyzes telemetry data
- Generates `Finding` objects with severity, evidence, and recommendations
- Triggers remediation plan generation

### Guided Remediation Flows

Remediation plans include:
- **Investigation steps**: Gather more context
- **Mitigation actions**: Fix the issue
- **Verification steps**: Confirm remediation worked
- **Risk flags**: Mark high-risk actions requiring approval

Example remediation plan structure:

```json
{
  "plan_id": "remediation-xyz",
  "title": "Latency Spike Remediation",
  "risk_level": "MEDIUM",
  "automated": false,
  "steps": [
    {
      "step": 1,
      "action": "Investigate Current Load",
      "command": "kubectl top pods",
      "requires_approval": false
    },
    {
      "step": 2,
      "action": "Scale Resources",
      "command": "kubectl scale deployment/app --replicas=5",
      "requires_approval": true
    }
  ]
}
```

### OWASP AI Security Checklist

The lab includes a comprehensive `docs/owasp_ai_checklist.yaml` that:

- Maps to OWASP Top 10 for LLM Applications
- Identifies applicable security controls
- Documents pass/fail status for each check
- Provides remediation guidance
- Suitable for security audits and compliance

**Check the checklist**:
```bash
cat docs/owasp_ai_checklist.yaml
```

---

## 4. Getting Started

### Requirements

- **Docker** (20.10+)
- **Docker Compose** (1.29+)
- **Python 3.11+** (if running notebooks locally)
- 2GB+ RAM for containers
- Ports 8080, 8081, 8082, 3000 available

### Quick Start

```bash
# Clone the repository
git clone https://github.com/<you>/ai-support-fabric-lab.git
cd ai-support-fabric-lab

# Copy environment template
cp .env.example .env

# Start all services
docker-compose up --build
```

Wait for services to start (30-60 seconds). You should see:

```
telemetry_collector_1 | Running on http://0.0.0.0:8081
agentic_ai_1          | Running on http://0.0.0.0:8082
gateway_1             | Running on http://0.0.0.0:8080
ui_dash_1             | Running on http://0.0.0.0:3000
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Gateway API** | http://localhost:8080 | Unified API endpoint |
| **Telemetry Collector** | http://localhost:8081 | Direct telemetry ingestion |
| **AI Engine API** | http://localhost:8082 | Detection and remediation APIs |
| **Dashboard** | http://localhost:3000 | Web UI for visualization |

### Verify Installation

```bash
# Check system health
curl http://localhost:8080/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "telemetry_collector": "healthy",
    "agentic_ai": "healthy"
  }
}
```

---

## 5. Running the Lab Scenarios

### Using Scenario Scripts

The `scripts/seed_scenarios.sh` script generates synthetic telemetry for demonstration:

```bash
# Run latency spike scenario
./scripts/seed_scenarios.sh scenario_latency_spike

# Run configuration drift scenario
./scripts/seed_scenarios.sh scenario_config_drift

# Run authentication error storm scenario
./scripts/seed_scenarios.sh scenario_auth_error_storm
```

### Example: Latency Spike Scenario

**Step 1**: Seed telemetry

```bash
./scripts/seed_scenarios.sh scenario_latency_spike
```

This generates:
- 15 log entries showing slow requests (5000-15000ms)
- 5 metric snapshots showing high CPU (85-99%)

**Step 2**: Trigger AI analysis

```bash
curl -X POST http://localhost:8080/api/run-analysis
```

**Step 3**: View findings

```bash
curl http://localhost:8080/api/ai/findings | jq
```

**Sample output**:

```json
{
  "findings": [
    {
      "finding_id": "latency-spike-1705318800.123",
      "severity": "HIGH",
      "title": "Latency Spike Detected",
      "description": "Detected 15 requests exceeding 1000ms threshold. Average duration: 9500ms.",
      "evidence": [...],
      "recommendations": [
        "Check application performance metrics",
        "Review database query performance",
        "Investigate external service dependencies",
        "Consider scaling resources if sustained high load"
      ]
    }
  ]
}
```

**Step 4**: View remediation plans

```bash
curl http://localhost:8080/api/ai/remediation | jq
```

**Step 5**: Check the dashboard

Open http://localhost:3000 to see:
- Finding severity badges
- Remediation plan steps
- System health status

### Where to See Output

#### API (Command Line)

```bash
# Findings (JSON)
curl http://localhost:8080/api/ai/findings

# Remediation plans (JSON)
curl http://localhost:8080/api/ai/remediation

# System status
curl http://localhost:8080/api/status
```

#### UI Dashboard

Navigate to http://localhost:3000:

- **System Status**: Service health, telemetry counts
- **Recent Findings**: Color-coded by severity (CRITICAL, HIGH, MEDIUM, LOW)
- **Remediation Plans**: Step-by-step guidance with risk indicators
- **Auto-refresh**: Updates every 30 seconds

---

## 6. Jupyter Notebooks

Interactive notebooks for hands-on learning:

### 01_overview.ipynb

Tour of the architecture and data model:
- System components and APIs
- Sending sample telemetry
- Querying telemetry data
- Understanding the data flow

### 02_detection_walkthrough.ipynb

Step-by-step walkthrough of detection logic:
- How LatencySpikeDetector works
- ConfigDriftDetector algorithm
- AuthFailureDetector patterns
- Creating custom detectors

### 03_guided_remediation.ipynb

From finding to recommended remediation:
- Remediation plan structure
- Risk levels and approval requirements
- Automated vs manual steps
- Best practices for remediation

### Running Notebooks

```bash
# Install Jupyter (if not already installed)
pip install jupyter requests

# Start Jupyter
jupyter notebook notebooks/

# Open and run each notebook interactively
```

---

## 7. Security & OWASP AI Checklist

### docs/owasp_ai_checklist.yaml

This lab demonstrates secure AI patterns and includes a comprehensive security checklist:

#### How to Review the Checklist

```bash
# View the full checklist
cat docs/owasp_ai_checklist.yaml

# Or use a YAML viewer
python3 -c "import yaml; print(yaml.dump(yaml.safe_load(open('docs/owasp_ai_checklist.yaml'))))"
```

#### How to Run It

The checklist is currently manual review. For automated checking:

1. **Review each category**: LLM01 through LLM10
2. **Check status**: PASS, FAIL, PARTIAL, NOT_APPLICABLE
3. **Read remediation**: Follow guidance for FAIL items
4. **Prioritize**: Focus on HIGH priority items first

#### Example Check

```yaml
- id: "LLM02-01"
  description: "Remediation commands are not auto-executed"
  status: "PASS"
  evidence: "All remediation plans are guidance-only, require manual execution"
```

### How the Lab Demonstrates Secure Patterns

1. **No Real Tokens**: All data is synthetic, no production credentials
2. **Minimal PII**: No personally identifiable information in telemetry
3. **Clear Separation**: Data (telemetry) vs model logic (detectors) are isolated
4. **Human-in-the-Loop**: High-risk remediation requires manual approval
5. **Audit Trail**: All telemetry includes timestamps and source tracking
6. **Input Validation**: API endpoints validate inputs before processing
7. **Principle of Least Privilege**: Containers run with minimal permissions

### Production Security Considerations

For production deployment, implement:

- **Authentication**: OAuth2/JWT for API access
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: TLS for all service communication
- **Secrets Management**: Vault/AWS Secrets Manager
- **Rate Limiting**: Prevent DoS attacks
- **Audit Logging**: Comprehensive logging for compliance
- **Vulnerability Scanning**: Regular dependency and container scans

See `docs/threat_model.md` for detailed threat analysis.

---

## 8. Extending the Lab

### Add New Telemetry Generators

**Location**: `lab/telemetry_collector/src/generators/synthetic_telemetry.py`

**Example**: Add a database slow query generator

```python
class DatabaseGenerator(TelemetryGenerator):
    """Generate database-related telemetry"""

    def generate_slow_query_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate slow database query logs"""
        logs = []
        for i in range(count):
            logs.append({
                'timestamp': self.generate_timestamp(offset_seconds=i*5),
                'service': self.service_name,
                'level': 'WARNING',
                'message': 'Database query exceeded timeout',
                'query_duration_ms': random.randint(3000, 10000),
                'query_type': random.choice(['SELECT', 'UPDATE', 'JOIN']),
                'table': f'users_table_{i}'
            })
        return logs
```

### Add New Detection Rules / Pseudo-Agents

**Location**: `lab/agentic_ai/src/detectors.py`

**Example**: Add a memory leak detector

```python
class MemoryLeakDetector:
    """Detect gradual memory increases"""

    def __init__(self, increase_threshold: float = 5.0, min_samples: int = 3):
        self.increase_threshold = increase_threshold
        self.min_samples = min_samples

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze for memory leaks"""
        memory_samples = []

        # Extract memory metrics
        for entry in telemetry:
            if entry.get('telemetry_type') == 'metric':
                data = entry.get('data', {})
                memory = data.get('metrics', {}).get('memory_percent')
                if memory:
                    memory_samples.append(memory)

        # Check for consistent increase
        if len(memory_samples) >= self.min_samples:
            increases = sum(1 for i in range(1, len(memory_samples))
                          if memory_samples[i] > memory_samples[i-1] + self.increase_threshold)

            if increases >= self.min_samples - 1:
                return Finding(
                    finding_id=f'memory-leak-{datetime.utcnow().timestamp()}',
                    severity='MEDIUM',
                    title='Potential Memory Leak Detected',
                    description=f'Memory increased {increases} consecutive times',
                    evidence=memory_samples,
                    recommendations=['Profile application', 'Check for resource leaks']
                )

        return None
```

**Register the detector** in `AnomalyDetectorEngine`:

```python
self.detectors = [
    LatencySpikeDetector(),
    ConfigDriftDetector(),
    AuthFailureDetector(),
    MemoryLeakDetector()  # Add here
]
```

### Plug in a Real LLM

**Location**: `lab/agentic_ai/src/detectors.py`

**Example**: Replace rule-based detection with Claude

```python
import anthropic

class LLMDetector:
    """Use Claude for anomaly detection"""

    def __init__(self, api_key: str):
        self.client = anthropic.Client(api_key=api_key)

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze telemetry using LLM"""
        prompt = f"""Analyze this telemetry for anomalies:

{json.dumps(telemetry[-50:], indent=2)}  # Last 50 entries

Identify issues and respond in JSON format:
{{
  "has_finding": true/false,
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "title": "Brief title",
  "description": "Detailed description",
  "recommendations": ["step1", "step2", ...]
}}
"""

        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)

        if result.get('has_finding'):
            return Finding(
                finding_id=f'llm-finding-{datetime.utcnow().timestamp()}',
                severity=result['severity'],
                title=result['title'],
                description=result['description'],
                evidence=telemetry[-5:],  # Include recent telemetry
                recommendations=result['recommendations']
            )

        return None
```

**TODOs for LLM Integration**:

- [ ] Add API key management (environment variables)
- [ ] Implement rate limiting for LLM calls
- [ ] Add error handling for API failures
- [ ] Cache LLM responses to reduce costs
- [ ] Add input/output guardrails
- [ ] Validate LLM JSON responses
- [ ] Monitor token usage and costs

---

## 9. License & Disclaimer

### License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) file for full text.

### Disclaimer

**FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY**

This lab is designed for:
- Learning about AI-driven operations
- Understanding agentic detection systems
- Experimenting with telemetry analysis
- Security research and education

**DO NOT deploy as-is to production** without:
- Comprehensive security hardening
- Authentication and authorization
- TLS/HTTPS encryption
- Rate limiting and DDoS protection
- Monitoring and alerting
- Compliance review (SOC2, GDPR, etc.)
- Professional security audit

**Use of synthetic data only**. Do not use with:
- Production credentials
- Real user data
- Sensitive information
- Regulated data (PII, PHI, PCI, etc.)

The authors assume no liability for:
- Security vulnerabilities
- Data breaches
- Service outages
- Compliance violations
- Damage from misuse

**Always follow your organization's security policies and consult security professionals before deployment.**

---

## 10. Additional Resources

### Documentation

| Document | Description |
|----------|-------------|
| [architecture.md](docs/architecture.md) | Detailed system design and data flow |
| [threat_model.md](docs/threat_model.md) | Security threat analysis (STRIDE) |
| [owasp_ai_checklist.yaml](docs/owasp_ai_checklist.yaml) | OWASP Top 10 for LLM compliance |
| [telemetry_schema.md](docs/telemetry_schema.md) | Telemetry data schemas and API docs |
| [lab_guide.md](docs/lab_guide.md) | Step-by-step lab exercises |

### Community

- **Issues**: Report bugs or request features via GitHub Issues
- **Discussions**: Share ideas and ask questions
- **Pull Requests**: Contribute improvements

### Related Projects

- **AIOps**: AI for IT Operations
- **Observability**: Prometheus, Grafana, Jaeger
- **Security Automation**: SOAR platforms
- **Chaos Engineering**: Gremlin, Chaos Monkey

### Learning Resources

- OWASP Top 10 for LLM Applications
- Site Reliability Engineering (SRE) practices
- Proactive incident management
- AI safety and alignment

---

## Quick Reference

### Common Commands

```bash
# Start lab
docker-compose up --build

# Stop lab
docker-compose down

# Reset lab (clear all data)
./scripts/reset_lab.sh

# Run scenario
./scripts/seed_scenarios.sh scenario_latency_spike

# Trigger analysis
curl -X POST http://localhost:8080/api/run-analysis

# View findings
curl http://localhost:8080/api/ai/findings | jq

# View remediation
curl http://localhost:8080/api/ai/remediation | jq

# Check health
curl http://localhost:8080/health
```

### Ports Reference

| Port | Service | Purpose |
|------|---------|---------|
| 8080 | Gateway | Main API entry point |
| 8081 | Telemetry Collector | Telemetry ingestion |
| 8082 | Agentic AI | Detection and remediation |
| 3000 | UI Dashboard | Web interface |

### Support

For help:

1. Check `docs/lab_guide.md` for exercises
2. Review logs: `docker-compose logs -f`
3. Open an issue on GitHub
4. Consult documentation in `docs/`

---

**Ready to begin?** Start with the [Lab Guide](docs/lab_guide.md) or jump straight into the [Quick Start](#4-getting-started)!
