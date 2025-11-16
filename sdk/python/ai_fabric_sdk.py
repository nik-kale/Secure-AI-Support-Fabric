"""
AI Support Fabric Python SDK

Simple client library for interacting with the AI Support Fabric Lab
"""
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Finding:
    """Represents a detection finding"""
    finding_id: str
    severity: str
    title: str
    description: str
    evidence: List[Dict]
    recommendations: List[str]
    detected_at: str


@dataclass
class RemediationPlan:
    """Represents a remediation plan"""
    plan_id: str
    finding_id: str
    title: str
    steps: List[Dict]
    risk_level: str


class AIFabricClient:
    """
    Client for AI Support Fabric Lab

    Example usage:
        client = AIFabricClient('http://localhost:8080')
        client.telemetry.log(service='my-app', level='INFO', message='Hello')
        findings = client.analysis.run()
    """

    def __init__(self, gateway_url: str = 'http://localhost:8080'):
        """
        Initialize client

        Args:
            gateway_url: URL of the gateway service
        """
        self.gateway_url = gateway_url.rstrip('/')
        self.telemetry = TelemetryClient(self)
        self.analysis = AnalysisClient(self)
        self.remediation = RemediationClient(self)

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        """Make HTTP request to API"""
        url = f"{self.gateway_url}{path}"
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def health(self) -> Dict:
        """Check system health"""
        return self._request('GET', '/health')


class TelemetryClient:
    """Telemetry operations"""

    def __init__(self, client: AIFabricClient):
        self.client = client

    def log(
        self,
        service: str,
        level: str,
        message: str,
        **kwargs
    ) -> Dict:
        """
        Send log telemetry

        Args:
            service: Service name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **kwargs: Additional fields (request_id, duration_ms, etc.)

        Returns:
            Response dict with telemetry_id
        """
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': service,
            'level': level,
            'message': message,
            **kwargs
        }

        return self.client._request('POST', '/api/telemetry/logs', json=data)

    def metrics(
        self,
        service: str,
        metrics: Dict[str, float]
    ) -> Dict:
        """
        Send metrics telemetry

        Args:
            service: Service name
            metrics: Dict of metric name -> value

        Returns:
            Response dict
        """
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': service,
            'metrics': metrics
        }

        return self.client._request('POST', '/api/telemetry/metrics', json=data)

    def config(
        self,
        service: str,
        config_version: str,
        configuration: Dict,
        changed_by: str,
        change_reason: str = ''
    ) -> Dict:
        """
        Send configuration change event

        Args:
            service: Service name
            config_version: Version identifier
            configuration: Configuration dict
            changed_by: Who made the change
            change_reason: Why the change was made

        Returns:
            Response dict
        """
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': service,
            'config_version': config_version,
            'configuration': configuration,
            'changed_by': changed_by,
            'change_reason': change_reason
        }

        return self.client._request('POST', '/api/telemetry/config', json=data)

    def query(
        self,
        telemetry_type: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None
    ) -> List[Dict]:
        """
        Query stored telemetry

        Args:
            telemetry_type: Filter by type ('log', 'metric', 'config')
            limit: Maximum results
            since: ISO timestamp to query from

        Returns:
            List of telemetry entries
        """
        params = {'limit': limit}
        if telemetry_type:
            params['type'] = telemetry_type
        if since:
            params['since'] = since

        response = self.client._request('GET', '/api/telemetry/query', params=params)
        return response.get('telemetry', [])

    def stats(self) -> Dict:
        """Get telemetry statistics"""
        response = self.client._request('GET', '/api/telemetry/stats')
        return response.get('statistics', {})


class AnalysisClient:
    """Analysis and detection operations"""

    def __init__(self, client: AIFabricClient):
        self.client = client

    def run(self) -> List[Finding]:
        """
        Trigger analysis and return findings

        Returns:
            List of Finding objects
        """
        response = self.client._request('POST', '/api/run-analysis')
        result = response.get('result', {})

        findings_data = result.get('findings', [])
        return [Finding(**f) for f in findings_data]

    def get_findings(self, limit: int = 50) -> List[Finding]:
        """
        Get recent findings

        Args:
            limit: Maximum results

        Returns:
            List of Finding objects
        """
        response = self.client._request('GET', f'/api/ai/findings?limit={limit}')
        findings_data = response.get('findings', [])
        return [Finding(**f) for f in findings_data]


class RemediationClient:
    """Remediation operations"""

    def __init__(self, client: AIFabricClient):
        self.client = client

    def get_plans(self, limit: int = 50) -> List[RemediationPlan]:
        """
        Get remediation plans

        Args:
            limit: Maximum results

        Returns:
            List of RemediationPlan objects
        """
        response = self.client._request('GET', f'/api/ai/remediation?limit={limit}')
        plans_data = response.get('remediation_plans', [])
        return [RemediationPlan(**p) for p in plans_data]

    def get_plan(self, finding_id: str) -> Optional[RemediationPlan]:
        """
        Get plan for specific finding

        Args:
            finding_id: Finding ID

        Returns:
            RemediationPlan or None
        """
        plans = self.get_plans()
        for plan in plans:
            if plan.finding_id == finding_id:
                return plan
        return None


# Convenience exports
__all__ = ['AIFabricClient', 'Finding', 'RemediationPlan']


# Example usage
if __name__ == '__main__':
    # Initialize client
    client = AIFabricClient('http://localhost:8080')

    # Check health
    health = client.health()
    print(f"System status: {health.get('status')}")

    # Send telemetry
    client.telemetry.log(
        service='my-app',
        level='INFO',
        message='Application started',
        request_id='start-001'
    )

    client.telemetry.metrics(
        service='my-app',
        metrics={
            'cpu_percent': 45.5,
            'memory_percent': 62.3
        }
    )

    # Run analysis
    findings = client.analysis.run()
    print(f"Found {len(findings)} issues")

    # Get remediation for findings
    for finding in findings:
        print(f"\nFinding: {finding.title} ({finding.severity})")
        plan = client.remediation.get_plan(finding.finding_id)
        if plan:
            print(f"Remediation: {plan.title}")
            for step in plan.steps:
                print(f"  {step['step']}. {step['action']}")
