"""
Remediation logic for generating guided remediation steps
This is a simulated "agentic" remediation system for educational purposes
"""
from typing import List, Dict, Any
from datetime import datetime

class RemediationPlan:
    """Represents a remediation plan for a finding"""

    def __init__(
        self,
        plan_id: str,
        finding_id: str,
        title: str,
        steps: List[Dict[str, Any]],
        automated: bool = False,
        risk_level: str = 'LOW'
    ):
        self.plan_id = plan_id
        self.finding_id = finding_id
        self.title = title
        self.steps = steps
        self.automated = automated
        self.risk_level = risk_level
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary"""
        return {
            'plan_id': self.plan_id,
            'finding_id': self.finding_id,
            'title': self.title,
            'steps': self.steps,
            'automated': self.automated,
            'risk_level': self.risk_level,
            'created_at': self.created_at
        }


class RemediationEngine:
    """Generate remediation plans based on findings"""

    def generate_plan(self, finding: Dict[str, Any]) -> RemediationPlan:
        """Generate remediation plan for a finding"""
        finding_id = finding.get('finding_id', '')
        title = finding.get('title', '')

        # Route to appropriate remediation strategy
        if 'latency' in title.lower():
            return self._remediate_latency_spike(finding)
        elif 'config' in title.lower() and 'drift' in title.lower():
            return self._remediate_config_drift(finding)
        elif 'auth' in title.lower():
            return self._remediate_auth_failures(finding)
        else:
            return self._generic_remediation(finding)

    def _remediate_latency_spike(self, finding: Dict[str, Any]) -> RemediationPlan:
        """Remediation plan for latency spikes"""
        steps = [
            {
                'step': 1,
                'action': 'Investigate Current Load',
                'description': 'Check current request rate and resource utilization',
                'command': 'kubectl top pods -n production',
                'automated': False
            },
            {
                'step': 2,
                'action': 'Review Application Metrics',
                'description': 'Examine APM traces to identify slow operations',
                'command': None,
                'automated': False
            },
            {
                'step': 3,
                'action': 'Check Database Performance',
                'description': 'Review slow query logs and connection pool status',
                'command': 'SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;',
                'automated': False
            },
            {
                'step': 4,
                'action': 'Scale Resources if Needed',
                'description': 'Increase replicas if sustained high load is detected',
                'command': 'kubectl scale deployment/app --replicas=5',
                'automated': False,
                'requires_approval': True
            },
            {
                'step': 5,
                'action': 'Monitor for Improvement',
                'description': 'Continue monitoring latency metrics for 15 minutes',
                'command': None,
                'automated': True
            }
        ]

        return RemediationPlan(
            plan_id=f'remediation-{finding["finding_id"]}',
            finding_id=finding['finding_id'],
            title='Latency Spike Remediation',
            steps=steps,
            automated=False,
            risk_level='MEDIUM'
        )

    def _remediate_config_drift(self, finding: Dict[str, Any]) -> RemediationPlan:
        """Remediation plan for configuration drift"""
        evidence = finding.get('evidence', [])
        drifts = []

        for change in evidence:
            drifts.extend(change.get('drifts', []))

        steps = [
            {
                'step': 1,
                'action': 'Verify Configuration Change',
                'description': f'Review the following configuration drifts: {", ".join(drifts[:3])}',
                'command': None,
                'automated': False
            },
            {
                'step': 2,
                'action': 'Check Change Authorization',
                'description': 'Verify if this change was authorized and documented',
                'command': None,
                'automated': False
            },
            {
                'step': 3,
                'action': 'Assess Security Impact',
                'description': 'Determine if drift introduces security vulnerabilities',
                'command': None,
                'automated': False
            },
            {
                'step': 4,
                'action': 'Rollback to Baseline (if unauthorized)',
                'description': 'Revert to known-good configuration if change is unauthorized',
                'command': 'kubectl apply -f config/baseline.yaml',
                'automated': False,
                'requires_approval': True
            },
            {
                'step': 5,
                'action': 'Enable Config Monitoring',
                'description': 'Ensure configuration change detection is active',
                'command': None,
                'automated': True
            },
            {
                'step': 6,
                'action': 'Document Change',
                'description': 'If authorized, update baseline and document the change',
                'command': None,
                'automated': False
            }
        ]

        return RemediationPlan(
            plan_id=f'remediation-{finding["finding_id"]}',
            finding_id=finding['finding_id'],
            title='Configuration Drift Remediation',
            steps=steps,
            automated=False,
            risk_level='HIGH'
        )

    def _remediate_auth_failures(self, finding: Dict[str, Any]) -> RemediationPlan:
        """Remediation plan for authentication failures"""
        evidence = finding.get('evidence', {})
        top_ips = evidence.get('top_ips', [])

        steps = [
            {
                'step': 1,
                'action': 'Enable Rate Limiting',
                'description': 'Temporarily enable aggressive rate limiting on auth endpoints',
                'command': 'kubectl apply -f config/rate-limit-strict.yaml',
                'automated': True,
                'requires_approval': False
            },
            {
                'step': 2,
                'action': 'Block Suspicious IPs',
                'description': f'Block top attacking IPs: {", ".join([ip[0] for ip in top_ips[:3]])}',
                'command': f'iptables -A INPUT -s {top_ips[0][0] if top_ips else "0.0.0.0"} -j DROP',
                'automated': False,
                'requires_approval': True
            },
            {
                'step': 3,
                'action': 'Enable Account Lockout',
                'description': 'Temporarily enable account lockout after 5 failed attempts',
                'command': None,
                'automated': False
            },
            {
                'step': 4,
                'action': 'Alert Security Team',
                'description': 'Send alert to security team for investigation',
                'command': None,
                'automated': True
            },
            {
                'step': 5,
                'action': 'Monitor Attack Progress',
                'description': 'Continue monitoring authentication failure rates',
                'command': None,
                'automated': True
            },
            {
                'step': 6,
                'action': 'Consider Enabling MFA',
                'description': 'For affected accounts, consider enforcing MFA',
                'command': None,
                'automated': False
            }
        ]

        return RemediationPlan(
            plan_id=f'remediation-{finding["finding_id"]}',
            finding_id=finding['finding_id'],
            title='Authentication Failure Storm Remediation',
            steps=steps,
            automated=False,
            risk_level='HIGH'
        )

    def _generic_remediation(self, finding: Dict[str, Any]) -> RemediationPlan:
        """Generic remediation plan"""
        recommendations = finding.get('recommendations', [])

        steps = []
        for i, rec in enumerate(recommendations, 1):
            steps.append({
                'step': i,
                'action': rec,
                'description': f'Follow recommendation: {rec}',
                'command': None,
                'automated': False
            })

        return RemediationPlan(
            plan_id=f'remediation-{finding["finding_id"]}',
            finding_id=finding['finding_id'],
            title='Generic Remediation Plan',
            steps=steps,
            automated=False,
            risk_level='MEDIUM'
        )
