"""
Main AI engine coordinating detection and remediation
This is a simplified "agentic" system using rules and mock AI logic
"""
import os
import requests
from typing import List, Dict, Any
from .detectors import AnomalyDetectorEngine
from .remediation import RemediationEngine
from .models import Finding, RemediationPlan

class AIEngine:
    """Main AI-Support Fabric engine"""

    def __init__(
        self,
        telemetry_collector_url: str = None
    ):
        self.telemetry_collector_url = telemetry_collector_url or os.getenv(
            'TELEMETRY_COLLECTOR_URL',
            'http://telemetry_collector:8081'
        )
        self.detector_engine = AnomalyDetectorEngine()
        self.remediation_engine = RemediationEngine()
        self.findings_cache = []
        self.remediation_cache = []

    def fetch_telemetry(
        self,
        telemetry_type: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch telemetry from collector"""
        try:
            params = {'limit': limit}
            if telemetry_type:
                params['type'] = telemetry_type

            response = requests.get(
                f'{self.telemetry_collector_url}/api/telemetry/query',
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('telemetry', [])
            else:
                print(f'Error fetching telemetry: {response.status_code}')
                return []

        except Exception as e:
            print(f'Exception fetching telemetry: {e}')
            return []

    def run_detection(self) -> List[Finding]:
        """Run detection on latest telemetry"""
        # Fetch telemetry from collector
        telemetry = self.fetch_telemetry(limit=200)

        if not telemetry:
            print('No telemetry data available')
            return []

        # Run detection
        findings = self.detector_engine.analyze_telemetry(telemetry)

        # Cache findings
        self.findings_cache.extend(findings)

        # Keep only last 100 findings
        self.findings_cache = self.findings_cache[-100:]

        return findings

    def generate_remediation_plans(
        self,
        findings: List[Finding] = None
    ) -> List[RemediationPlan]:
        """Generate remediation plans for findings"""
        if findings is None:
            # Use cached findings
            findings = self.findings_cache

        plans = []
        for finding in findings:
            plan = self.remediation_engine.generate_plan(finding.to_dict())
            plans.append(plan)

        # Cache plans
        self.remediation_cache.extend(plans)
        self.remediation_cache = self.remediation_cache[-100:]

        return plans

    def get_findings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get cached findings"""
        return [f.to_dict() for f in self.findings_cache[-limit:]]

    def get_remediation_plans(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get cached remediation plans"""
        return [p.to_dict() for p in self.remediation_cache[-limit:]]

    def analyze_and_remediate(self) -> Dict[str, Any]:
        """Full analysis and remediation cycle"""
        # Run detection
        findings = self.run_detection()

        # Generate remediation plans
        plans = self.generate_remediation_plans(findings)

        return {
            'findings_count': len(findings),
            'findings': [f.to_dict() for f in findings],
            'remediation_plans_count': len(plans),
            'remediation_plans': [p.to_dict() for p in plans]
        }
