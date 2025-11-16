# AI Support Fabric - Lab Guide

## Welcome to the Lab!

This hands-on lab will teach you about AI-driven proactive support using synthetic telemetry, agentic detection, and guided remediation. By the end, you'll understand how modern AI systems can detect issues and suggest fixes automatically.

## Learning Objectives

After completing this lab, you will be able to:

1. Understand the architecture of an AI-driven support fabric
2. Generate and ingest synthetic telemetry data
3. Trigger AI-based anomaly detection
4. Interpret detection findings and evidence
5. Review and understand guided remediation plans
6. Extend the lab with custom detectors

## Prerequisites

### Required

- Docker and Docker Compose installed
- Basic understanding of REST APIs
- Familiarity with command line
- Text editor or IDE

### Optional

- Python 3.11+ (for notebooks)
- Jupyter (for interactive notebooks)
- curl or Postman (for API testing)
- Basic understanding of microservices

## Lab Setup

### Step 1: Clone and Start

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd ai-support-fabric-lab

# Copy environment template
cp .env.example .env

# Start all services
docker-compose up --build
```

Wait for all services to start. You should see:
```
telemetry_collector_1 | Running on http://0.0.0.0:8081
agentic_ai_1          | Running on http://0.0.0.0:8082
gateway_1             | Running on http://0.0.0.0:8080
ui_dash_1             | Running on http://0.0.0.0:3000
```

### Step 2: Verify Services

Check that all services are healthy:

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "telemetry_collector": "healthy",
    "agentic_ai": "healthy"
  }
}
```

### Step 3: Open the Dashboard

Navigate to http://localhost:3000 in your browser. You should see the AI Support Fabric dashboard with empty statistics.

## Exercise 1: Understanding Telemetry

### Objective
Learn how to send telemetry data to the collector.

### Steps

1. **Send a log entry:**

```bash
curl -X POST http://localhost:8080/api/telemetry/logs \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2025-01-15T10:30:00Z",
    "service": "my-first-service",
    "level": "INFO",
    "message": "Hello from the lab!",
    "request_id": "lab-001",
    "duration_ms": 125
  }'
```

2. **Send metrics:**

```bash
curl -X POST http://localhost:8080/api/telemetry/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2025-01-15T10:30:00Z",
    "service": "my-first-service",
    "metrics": {
      "cpu_percent": 45.5,
      "memory_percent": 52.3,
      "request_rate": 100
    }
  }'
```

3. **Query your telemetry:**

```bash
curl http://localhost:8080/api/telemetry/query?limit=5
```

4. **Check statistics:**

```bash
curl http://localhost:8080/api/telemetry/stats
```

### Questions to Explore

- What happens if you send invalid JSON?
- What fields are required vs optional?
- How does the collector enrich your data?

## Exercise 2: Latency Spike Detection

### Objective
Generate a latency spike scenario and see how the AI detects it.

### Steps

1. **Generate latency spike telemetry:**

```bash
./scripts/seed_scenarios.sh scenario_latency_spike
```

This script sends 15 log entries showing slow requests (5-15 seconds each) and 5 metrics showing high CPU usage.

2. **Trigger AI analysis:**

```bash
curl -X POST http://localhost:8080/api/run-analysis
```

3. **View findings:**

```bash
curl http://localhost:8080/api/ai/findings | jq
```

You should see a finding like:

```json
{
  "finding_id": "latency-spike-...",
  "severity": "HIGH",
  "title": "Latency Spike Detected",
  "description": "Detected 15 requests exceeding 1000ms threshold...",
  "evidence": [...],
  "recommendations": [
    "Check application performance metrics",
    "Review database query performance",
    ...
  ]
}
```

4. **View remediation plan:**

```bash
curl http://localhost:8080/api/ai/remediation | jq
```

5. **Check the dashboard:**

Open http://localhost:3000 to see the visual representation.

### Analysis Questions

- What threshold does the detector use?
- How many slow requests are needed to trigger?
- What remediation steps are suggested?
- Which steps require approval?

## Exercise 3: Configuration Drift Detection

### Objective
Simulate a security configuration change and detect drift.

### Steps

1. **Generate config drift:**

```bash
./scripts/seed_scenarios.sh scenario_config_drift
```

This sends a configuration with `debug_mode: true` and `log_level: DEBUG`, which drift from the secure baseline.

2. **Run analysis:**

```bash
curl -X POST http://localhost:8080/api/run-analysis
```

3. **Examine the finding:**

```bash
curl http://localhost:8080/api/ai/findings | jq '.findings[] | select(.title | contains("Config"))'
```

Look for:
- Severity level (should be CRITICAL or MEDIUM)
- Specific drifts detected
- Evidence showing before/after

4. **Review remediation:**

```bash
curl http://localhost:8080/api/ai/remediation | jq '.remediation_plans[] | select(.title | contains("Config"))'
```

### Analysis Questions

- Why is config drift considered CRITICAL?
- What is the baseline configuration?
- What remediation steps involve verification?
- Why does rollback require approval?

## Exercise 4: Authentication Failure Storm

### Objective
Simulate a brute-force attack and observe detection.

### Steps

1. **Generate auth failures:**

```bash
./scripts/seed_scenarios.sh scenario_auth_error_storm
```

This simulates 30 failed login attempts from 2 IPs targeting 3 users.

2. **Analyze:**

```bash
curl -X POST http://localhost:8080/api/run-analysis
```

3. **Examine findings:**

```bash
curl http://localhost:8080/api/ai/findings | jq '.findings[] | select(.title | contains("Auth"))'
```

Look for:
- Total failures detected
- Number of unique users
- Number of unique IPs
- Top attacking IPs

4. **Study remediation:**

Review the suggested steps - notice some are marked as `automated: true` (like rate limiting) while others require approval (like IP blocking).

### Analysis Questions

- What pattern indicates a brute-force attack?
- Why are some remediation steps automated?
- What's the risk of automatically blocking IPs?
- How would you verify this is a real attack?

## Exercise 5: Using Jupyter Notebooks

### Objective
Explore the lab interactively using Jupyter notebooks.

### Steps

1. **Install Jupyter:**

```bash
pip install jupyter requests
```

2. **Start Jupyter:**

```bash
jupyter notebook notebooks/
```

3. **Open and run each notebook:**
   - `01_overview.ipynb` - Architecture overview
   - `02_detection_walkthrough.ipynb` - Step-through detection
   - `03_guided_remediation.ipynb` - Remediation deep-dive

4. **Experiment:**
   - Modify thresholds
   - Create custom telemetry
   - Mix multiple scenarios

## Exercise 6: Extending the Lab

### Objective
Add a custom detector for a new type of anomaly.

### Challenge: Memory Leak Detector

Create a detector that identifies gradual memory increases over time.

### Steps

1. **Open the detectors file:**

```bash
lab/agentic_ai/src/detectors.py
```

2. **Add a new detector class:**

```python
class MemoryLeakDetector:
    """Detect gradual memory increases indicating a leak"""

    def __init__(self, increase_threshold: float = 5.0, min_samples: int = 3):
        self.increase_threshold = increase_threshold
        self.min_samples = min_samples

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze telemetry for memory leaks"""
        memory_samples = []

        # Extract memory metrics
        for entry in telemetry:
            if entry.get('telemetry_type') == 'metric':
                data = entry.get('data', {})
                metrics = data.get('metrics', {})
                memory = metrics.get('memory_percent')

                if memory:
                    memory_samples.append({
                        'timestamp': data.get('timestamp'),
                        'memory': memory
                    })

        # Sort by timestamp
        memory_samples.sort(key=lambda x: x['timestamp'])

        # Check for consistent increase
        if len(memory_samples) < self.min_samples:
            return None

        increases = 0
        for i in range(1, len(memory_samples)):
            if memory_samples[i]['memory'] > memory_samples[i-1]['memory'] + self.increase_threshold:
                increases += 1

        if increases >= self.min_samples - 1:
            return Finding(
                finding_id=f'memory-leak-{datetime.utcnow().timestamp()}',
                severity='MEDIUM',
                title='Potential Memory Leak Detected',
                description=f'Memory usage increased consistently across {increases} intervals',
                evidence=memory_samples,
                recommendations=[
                    'Review application memory usage patterns',
                    'Check for unclosed resources or connections',
                    'Profile application for memory leaks',
                    'Consider increasing memory limits if legitimate growth'
                ]
            )

        return None
```

3. **Register the detector:**

In `AnomalyDetectorEngine.__init__`:

```python
self.detectors = [
    LatencySpikeDetector(),
    ConfigDriftDetector(),
    AuthFailureDetector(),
    MemoryLeakDetector()  # Add this line
]
```

4. **Rebuild and test:**

```bash
docker-compose down
docker-compose up --build
```

5. **Generate test data:**

Create a script to send gradually increasing memory metrics, then run analysis.

## Exercise 7: Dashboard Exploration

### Objective
Understand the real-time monitoring capabilities.

### Steps

1. **Open dashboard:** http://localhost:3000

2. **Observe auto-refresh:** The dashboard updates every 30 seconds

3. **Trigger multiple scenarios:**

```bash
./scripts/seed_scenarios.sh scenario_latency_spike
sleep 5
./scripts/seed_scenarios.sh scenario_config_drift
sleep 5
./scripts/seed_scenarios.sh scenario_auth_error_storm
```

4. **Click "Run Analysis" button**

5. **Observe:**
   - Finding severity badges (color-coded)
   - Remediation plan steps
   - Telemetry statistics

## Troubleshooting

### Services Won't Start

**Symptom:** Docker compose fails to start services

**Solutions:**
- Check ports 8080, 8081, 8082, 3000 aren't already in use
- Run `docker-compose down` to clean up
- Check Docker has enough resources (2GB+ RAM recommended)

### No Findings Generated

**Symptom:** Analysis runs but no findings appear

**Solutions:**
- Verify telemetry was ingested: `curl http://localhost:8080/api/telemetry/stats`
- Check you're querying recent findings: `curl http://localhost:8080/api/ai/findings?limit=50`
- Ensure you ran analysis after seeding: `curl -X POST http://localhost:8080/api/run-analysis`

### Dashboard Shows Empty

**Symptom:** UI dashboard shows no data

**Solutions:**
- Check gateway is reachable from UI container
- Verify findings exist via API
- Check browser console for errors
- Try hard refresh (Ctrl+Shift+R)

### Script Permission Denied

**Symptom:** `./scripts/seed_scenarios.sh: Permission denied`

**Solution:**
```bash
chmod +x scripts/*.sh
```

## Best Practices

### When Running Scenarios

1. **One at a time:** Run scenarios individually to see clear findings
2. **Clear between runs:** Use `./scripts/reset_lab.sh` to start fresh
3. **Analyze after seeding:** Always trigger analysis after seeding telemetry
4. **Check dashboard:** Visual feedback is easier to understand

### When Developing Detectors

1. **Start simple:** Begin with threshold-based rules
2. **Test with known data:** Use scenario generators for consistent testing
3. **Handle edge cases:** What if telemetry is empty?
4. **Provide evidence:** Always include evidence in findings
5. **Clear recommendations:** Make remediation actionable

### When Extending

1. **Document schemas:** Update telemetry_schema.md with new fields
2. **Update notebooks:** Add examples to Jupyter notebooks
3. **Write tests:** Add unit tests for new detectors
4. **Version changes:** Use git tags for versions

## Advanced Topics

### Integrating Real LLMs

To replace rule-based detection with actual LLM:

1. **Choose provider:** OpenAI, Anthropic, etc.
2. **Add API client:** Install SDK (e.g., `anthropic` package)
3. **Create prompt:** Structure telemetry as context
4. **Parse response:** Extract findings from LLM output
5. **Add guardrails:** Validate LLM suggestions

Example:

```python
import anthropic

def analyze_with_claude(telemetry):
    client = anthropic.Client(api_key="...")

    prompt = f"""Analyze this telemetry for anomalies:

{json.dumps(telemetry, indent=2)}

Identify any issues and provide:
1. Severity (CRITICAL/HIGH/MEDIUM/LOW)
2. Title
3. Description
4. Remediation steps
"""

    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    return parse_llm_finding(response.content)
```

### Production Deployment

To deploy beyond the lab:

1. **Security:**
   - Enable HTTPS/TLS
   - Add authentication (OAuth2/JWT)
   - Implement RBAC
   - Secrets management

2. **Scalability:**
   - Replace SQLite with PostgreSQL
   - Add message queue (Kafka/RabbitMQ)
   - Use Redis for caching
   - Deploy to Kubernetes

3. **Observability:**
   - Centralized logging (ELK/Splunk)
   - Metrics (Prometheus/Grafana)
   - Distributed tracing (Jaeger)
   - Alerting (PagerDuty/Slack)

4. **Reliability:**
   - High availability setup
   - Backup and disaster recovery
   - Rate limiting and throttling
   - Circuit breakers

## Next Steps

After completing the lab:

1. **Read the Documentation:**
   - `docs/architecture.md` - Deep dive into design
   - `docs/threat_model.md` - Security considerations
   - `docs/owasp_ai_checklist.yaml` - AI security checklist

2. **Experiment:**
   - Create your own scenarios
   - Add custom detectors
   - Modify remediation logic
   - Integrate with real services

3. **Share:**
   - Present findings to your team
   - Adapt concepts to your infrastructure
   - Contribute improvements back

4. **Explore Related Topics:**
   - AIOps and observability
   - Chaos engineering
   - Site reliability engineering
   - Security automation (SOAR)

## Resources

### Documentation

- Architecture: `docs/architecture.md`
- Threat Model: `docs/threat_model.md`
- OWASP Checklist: `docs/owasp_ai_checklist.yaml`
- Telemetry Schema: `docs/telemetry_schema.md`

### Code

- Detectors: `lab/agentic_ai/src/detectors.py`
- Remediation: `lab/agentic_ai/src/remediation.py`
- Generators: `lab/telemetry_collector/src/generators/`

### APIs

- Gateway: http://localhost:8080
- Telemetry: http://localhost:8081
- AI Engine: http://localhost:8082
- Dashboard: http://localhost:3000

## Feedback and Contributions

This is an educational lab designed for learning. If you:

- Find bugs or issues
- Have suggestions for improvements
- Want to add features
- Need help or clarification

Please open an issue or submit a pull request!

## Conclusion

Congratulations on completing the AI Support Fabric Lab! You now understand:

- How AI can proactively detect operational issues
- The architecture of an AI-driven support system
- How to generate and analyze synthetic telemetry
- How guided remediation helps operators respond to incidents

These concepts form the foundation of modern AIOps and proactive support systems used in production by leading tech companies.

Happy learning! 🚀
