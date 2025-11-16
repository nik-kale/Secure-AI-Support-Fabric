# Quick Start Guide - AI Support Fabric Lab v2.0

Get up and running with all the new features in 5 minutes!

---

## Prerequisites

```bash
- Docker & Docker Compose
- Python 3.11+
- Git
```

---

## 1. Basic Setup (2 minutes)

```bash
# Clone and start
git clone <repo-url>
cd ai-support-fabric-lab
cp .env.example .env
docker-compose up --build
```

**Wait for**: All services showing "Running on http://..."

---

## 2. Run Your First Test (1 minute)

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run tests
pytest tests/unit/test_detectors.py -v

# Expected output: All tests PASSED ✅
```

---

## 3. Try the Python SDK (1 minute)

```bash
# Install SDK
pip install requests

# Create test script
cat > test_sdk.py << 'EOF'
import sys
sys.path.insert(0, './sdk/python')
from ai_fabric_sdk import AIFabricClient

# Initialize client
client = AIFabricClient('http://localhost:8080')

# Send telemetry
client.telemetry.log(
    service='quickstart',
    level='INFO',
    message='Hello from SDK!'
)

# Run analysis
findings = client.analysis.run()
print(f"✅ SDK works! Found {len(findings)} findings")
EOF

# Run it
python test_sdk.py
```

---

## 4. Create Your First Plugin (1 minute)

```bash
# Create plugin file
cat > plugins/hello_detector.py << 'EOF'
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lab/agentic_ai/src'))

from plugins.base import DetectorPlugin, PluginMetadata, Finding
from datetime import datetime

class HelloDetector(DetectorPlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="hello_detector",
            version="1.0.0",
            author="You",
            description="Example detector",
            category="demo"
        )

    def analyze(self, telemetry):
        # Detect if any log contains "hello"
        for entry in telemetry:
            if entry.get('telemetry_type') == 'log':
                msg = entry.get('data', {}).get('message', '')
                if 'hello' in msg.lower():
                    return Finding(
                        finding_id=f'hello-{datetime.utcnow().timestamp()}',
                        severity='LOW',
                        title='Hello Detected!',
                        description='Found a friendly greeting',
                        evidence=[entry],
                        recommendations=['Say hello back!']
                    )
        return None
EOF

# Test your plugin
python -c "
import sys
sys.path.insert(0, './lab/agentic_ai/src')
from plugins import PluginManager

manager = PluginManager(['./plugins'])
manager.load_plugins()
print('✅ Loaded plugins:', [p.name for p in manager.list_plugins()])
"
```

---

## 5. Try LLM Integration (Optional)

```bash
# Install LLM support
pip install anthropic  # or openai

# Set API key
export ANTHROPIC_API_KEY='your-key-here'

# Test LLM provider
python << 'EOF'
import sys, asyncio
sys.path.insert(0, './lab/agentic_ai/src')

from llm import create_provider

async def test():
    provider = create_provider('anthropic')

    # Simple test telemetry
    telemetry = [{
        'telemetry_type': 'log',
        'data': {
            'level': 'ERROR',
            'message': 'Database connection failed',
            'duration_ms': 5000
        }
    }]

    result = await provider.analyze_telemetry(telemetry)
    print(f"✅ LLM analysis: {result}")

asyncio.run(test())
EOF
```

---

## 6. Run a Complete Scenario

```bash
# Seed latency spike scenario
./scripts/seed_scenarios.sh scenario_latency_spike

# Trigger analysis (with all new features!)
curl -X POST http://localhost:8080/api/run-analysis

# View findings
curl http://localhost:8080/api/ai/findings | jq '.findings[0]'

# Open dashboard
open http://localhost:3000
```

---

## Next Steps

### Explore New Features

1. **Testing**: `pytest -v` - Run full test suite
2. **Plugins**: Check `plugins/examples/` for more examples
3. **ML Detection**: See `lab/ml_models/anomaly_detection.py`
4. **SDK**: Explore `sdk/python/ai_fabric_sdk.py`
5. **LLM**: Try different providers in `lab/agentic_ai/src/llm/`

### Read Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - All new features explained
- [docs/lab_guide.md](docs/lab_guide.md) - Detailed tutorials
- [docs/architecture.md](docs/architecture.md) - System design

### Contribute

- Create custom plugins in `plugins/`
- Add tests in `tests/`
- Submit PRs with improvements

---

## Troubleshooting

### Tests Fail

```bash
# Ensure services are running
docker-compose ps

# Check logs
docker-compose logs telemetry_collector

# Restart services
docker-compose restart
```

### Plugin Won't Load

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify plugin syntax
python -m py_compile plugins/your_plugin.py

# Check plugin manager logs
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from plugins import PluginManager
PluginManager(['./plugins']).load_plugins()
"
```

### LLM Not Working

```bash
# Verify API key
echo $ANTHROPIC_API_KEY

# Test connection
pip install anthropic
python -c "from anthropic import Anthropic; print(Anthropic().messages.create(model='claude-3-haiku-20240307', max_tokens=10, messages=[{'role':'user','content':'hi'}]))"
```

---

## Get Help

- **Issues**: Open a GitHub issue
- **Questions**: Check [docs/lab_guide.md](docs/lab_guide.md)
- **Examples**: See `plugins/examples/` and `sdk/python/`

---

**You're all set! 🚀**

The AI Support Fabric Lab is now running with:
- ✅ Automated testing
- ✅ LLM integration
- ✅ Plugin system
- ✅ ML anomaly detection
- ✅ Python SDK
- ✅ CI/CD pipeline

Enjoy exploring the next-level features!
