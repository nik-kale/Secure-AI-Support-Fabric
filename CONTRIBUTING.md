# Contributing to Secure AI Support Fabric

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [How to Contribute](#how-to-contribute)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level
- Background
- Identity
- Nationality

### Expected Behavior

- Be respectful and constructive
- Welcome newcomers
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.11+** installed
- **Docker** and **Docker Compose**
- **Git** for version control
- Basic understanding of:
  - Python and Flask
  - Docker containers
  - SQLite databases
  - OpenTelemetry concepts (helpful but not required)

### Finding Issues to Work On

1. Check the [Issues](https://github.com/nik-kale/Secure-AI-Support-Fabric/issues) page
2. Look for labels:
   - `good first issue` - Great for newcomers
   - `help wanted` - We need contributors
   - `bug` - Something isn't working
   - `enhancement` - New feature or request
   - `documentation` - Improvements or additions to docs

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/Secure-AI-Support-Fabric.git
cd Secure-AI-Support-Fabric

# Add upstream remote
git remote add upstream https://github.com/nik-kale/Secure-AI-Support-Fabric.git
```

### 2. Create Development Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
# or for bug fixes
git checkout -b fix/issue-description
```

### 3. Install Development Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 4. Set Up Environment

```bash
# Copy example environment
cp .env.example .env

# Edit with your settings
nano .env
```

### 5. Start Development Environment

```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## How to Contribute

### Types of Contributions

#### 1. Bug Reports

When filing a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the bug
- **Expected behavior** vs actual behavior
- **Environment details**:
  - OS and version
  - Python version
  - Docker version
  - Relevant logs
- **Screenshots** if applicable

**Template**:
```markdown
**Bug Description**
[Clear description of the bug]

**Steps to Reproduce**
1. Start service X
2. Send request to endpoint Y
3. Observe error Z

**Expected Behavior**
[What should happen]

**Actual Behavior**
[What actually happens]

**Environment**
- OS: Ubuntu 22.04
- Python: 3.11.5
- Docker: 24.0.5

**Logs**
```
[Paste relevant logs]
```
```

#### 2. Feature Requests

For feature requests, provide:

- **Use case** - Why is this needed?
- **Proposed solution** - How should it work?
- **Alternatives considered** - Other approaches
- **Impact** - Who benefits?

#### 3. Code Contributions

See [Pull Request Process](#pull-request-process) below.

#### 4. Documentation Improvements

Documentation contributions are highly valued:

- Fix typos or clarify existing docs
- Add examples and tutorials
- Improve API documentation
- Translate documentation
- Add diagrams or visualizations

---

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://peps.python.org/pep-0008/) with these specifics:

**Line Length**: 100 characters maximum

**Imports**:
```python
# Standard library
import os
import sys
from typing import List, Dict, Optional

# Third-party
import flask
from marshmallow import Schema

# Local
from lab.common.logging_config import setup_logging
```

**Type Hints**:
```python
def process_telemetry(data: Dict[str, Any]) -> List[Finding]:
    """Process telemetry data and return findings."""
    pass
```

**Docstrings**:
```python
def analyze_metric(metric: Dict) -> bool:
    """
    Analyze a single metric for anomalies.

    Args:
        metric: Dictionary containing metric data with keys:
            - name: Metric name (str)
            - value: Metric value (float)
            - timestamp: Unix timestamp (int)

    Returns:
        True if anomaly detected, False otherwise

    Raises:
        ValueError: If metric is missing required fields
    """
    pass
```

### Code Formatting

We use **Black** for consistent formatting:

```bash
# Format all code
black lab/

# Check without modifying
black --check lab/
```

### Linting

We use **flake8** for linting:

```bash
# Lint all code
flake8 lab/

# With specific config
flake8 --config=.flake8 lab/
```

### Type Checking

We use **mypy** for static type checking:

```bash
# Type check all code
mypy lab/

# Strict mode
mypy --strict lab/
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lab --cov-report=html

# Run specific test file
pytest tests/test_detectors.py

# Run specific test
pytest tests/test_detectors.py::test_latency_detector

# Verbose output
pytest -v
```

### Writing Tests

**Test Structure**:
```python
import pytest
from lab.agentic_ai.src.detectors import LatencySpikeDetector

class TestLatencySpikeDetector:
    """Tests for LatencySpikeDetector"""

    @pytest.fixture
    def detector(self):
        """Create detector instance"""
        return LatencySpikeDetector(threshold_ms=1000, min_occurrences=3)

    def test_detect_latency_spike(self, detector):
        """Test that latency spikes are detected"""
        # Arrange
        telemetry = [
            {'duration_ms': 5000, 'timestamp': 1000},
            {'duration_ms': 6000, 'timestamp': 2000},
            {'duration_ms': 7000, 'timestamp': 3000},
        ]

        # Act
        finding = detector.analyze(telemetry)

        # Assert
        assert finding is not None
        assert finding.severity == 'HIGH'
        assert 'latency' in finding.title.lower()

    def test_no_spike_below_threshold(self, detector):
        """Test that no finding is generated below threshold"""
        # Arrange
        telemetry = [
            {'duration_ms': 100, 'timestamp': 1000},
            {'duration_ms': 200, 'timestamp': 2000},
        ]

        # Act
        finding = detector.analyze(telemetry)

        # Assert
        assert finding is None
```

### Test Coverage

Maintain **75%+ test coverage** for all new code:

```bash
# Generate coverage report
pytest --cov=lab --cov-report=term-missing

# Open HTML report
open htmlcov/index.html
```

---

## Documentation

### API Documentation

Document all public APIs:

```python
@app.route('/api/traces/<trace_id>', methods=['GET'])
@rate_limit(tier='query', max_requests=1000, window_seconds=3600)
@require_auth
def get_trace_detail(trace_id: str):
    """
    Get detailed trace data with visualization structure.

    Args:
        trace_id: Unique trace identifier

    Returns:
        JSON response with trace tree, metadata, and analysis

    Example:
        GET /api/traces/abc123?include_analysis=true

        Response:
        {
          "success": true,
          "trace": {
            "metadata": {...},
            "tree": {...},
            "analysis": {...}
          }
        }

    Rate Limit:
        1000 requests per hour per API key

    Authentication:
        Requires valid X-API-Key header

    Errors:
        - 404: Trace not found
        - 500: Internal server error
    """
    pass
```

### Markdown Documentation

- Use clear headings
- Include code examples
- Add diagrams where helpful
- Keep line length reasonable (80-100 chars)
- Use tables for structured data

---

## Pull Request Process

### 1. Prepare Your Changes

```bash
# Make sure you're on your feature branch
git checkout feature/your-feature

# Make your changes
# ...

# Run tests
pytest

# Format code
black lab/
flake8 lab/

# Commit changes
git add .
git commit -m "feat: add new feature"
```

### 2. Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semi-colons, etc)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding missing tests
- `chore`: Changes to build process or auxiliary tools

**Examples**:
```bash
feat(otel): add trace aggregation endpoint

Implements a new endpoint for aggregating trace data
over time windows. Supports hourly, daily, and weekly
aggregation.

Closes #123

---

fix(correlator): use total_seconds() instead of seconds

The .seconds attribute only returns 0-86399, causing
incorrect correlation for alerts >24 hours apart.

Fixes #456

---

docs: update API documentation for v2.2 features

- Add trace visualizer endpoints
- Add examples for service topology
- Update performance benchmarks
```

### 3. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature

# Create pull request on GitHub
# Go to: https://github.com/nik-kale/Secure-AI-Support-Fabric/pulls
# Click "New Pull Request"
```

### 4. PR Description Template

```markdown
## Description
[Describe what this PR does]

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Fixes #123
Closes #456

## How Has This Been Tested?
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

**Test Configuration**:
- OS: Ubuntu 22.04
- Python: 3.11.5
- Docker: 24.0.5

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
[Add screenshots here]

## Additional Notes
[Any additional information]
```

### 5. Review Process

**What to Expect**:
1. Automated checks run (tests, linting)
2. Maintainer reviews code
3. Feedback provided if changes needed
4. Once approved, PR is merged

**Responding to Feedback**:
```bash
# Make requested changes
# ...

# Commit and push
git add .
git commit -m "fix: address review comments"
git push origin feature/your-feature
```

---

## Development Workflow

### Daily Development

```bash
# 1. Update your branch
git checkout main
git pull upstream main
git checkout feature/your-feature
git rebase main

# 2. Make changes
# ...

# 3. Test locally
pytest
black lab/
flake8 lab/

# 4. Commit
git add .
git commit -m "feat: your change"

# 5. Push regularly
git push origin feature/your-feature
```

### Before Creating PR

- [ ] All tests pass
- [ ] Code is formatted (Black)
- [ ] No linting errors (flake8)
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] Branch is up-to-date with main

---

## Architecture Guidelines

### Adding New Services

When adding a new microservice:

1. Create directory: `lab/your_service/`
2. Add structure:
```
lab/your_service/
├── __init__.py
├── Dockerfile
├── requirements.txt
└── src/
    ├── __init__.py
    └── main.py
```
3. Update `docker-compose.yml`
4. Add documentation to README
5. Add health check endpoint
6. Implement authentication
7. Add rate limiting
8. Add logging

### Adding New Detectors

```python
# lab/agentic_ai/src/detectors/your_detector.py
from lab.agentic_ai.src.models import Finding
from typing import List, Dict, Optional

class YourDetector:
    """
    Detects specific anomaly pattern.

    This detector analyzes telemetry for [specific pattern]
    and generates findings when [condition] is met.
    """

    def __init__(self, threshold: float = 100.0):
        """
        Initialize detector.

        Args:
            threshold: Detection threshold
        """
        self.threshold = threshold

    def analyze(self, telemetry: List[Dict]) -> Optional[Finding]:
        """
        Analyze telemetry for anomalies.

        Args:
            telemetry: List of telemetry events

        Returns:
            Finding if anomaly detected, None otherwise
        """
        # Your detection logic
        pass
```

---

## Security Guidelines

### Security Best Practices

1. **Never commit secrets**:
   - Use `.env` for sensitive data
   - Add secrets to `.gitignore`
   - Use environment variables

2. **Validate all inputs**:
   - Use Marshmallow schemas
   - Sanitize user input
   - Prevent SQL injection

3. **Use parameterized queries**:
```python
# Good
cursor.execute('SELECT * FROM logs WHERE id = ?', (log_id,))

# Bad - SQL injection risk
cursor.execute(f'SELECT * FROM logs WHERE id = {log_id}')
```

4. **Implement authentication**:
   - Use `@require_auth` decorator
   - Validate API keys properly
   - Log authentication failures

5. **Rate limiting**:
   - Apply to all public endpoints
   - Use appropriate limits
   - Return 429 when exceeded

### Reporting Security Issues

**DO NOT** create public issues for security vulnerabilities.

Instead, email: security@example.com with:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours.

---

## Release Process

Maintainers follow this process for releases:

1. Update version in all relevant files
2. Update CHANGELOG.md
3. Create release branch
4. Run full test suite
5. Build and test Docker images
6. Create GitHub release
7. Tag with semantic version
8. Deploy to production

---

## Getting Help

Need help contributing?

- **Documentation**: Check the `docs/` directory
- **Discord/Slack**: [Coming soon]
- **GitHub Discussions**: Ask questions
- **Stack Overflow**: Tag with `secure-ai-support-fabric`

---

## Recognition

Contributors are recognized in:

- README.md Contributors section
- CHANGELOG.md for each release
- GitHub contributors graph
- Yearly contributor highlights

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🎉
