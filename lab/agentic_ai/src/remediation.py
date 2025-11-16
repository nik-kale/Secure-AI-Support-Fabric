"""
Remediation logic for generating guided remediation steps
This is a simulated "agentic" remediation system for educational purposes

SECURITY: All infrastructure commands are whitelisted and require approval.
No commands are automated by default.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from .models import RemediationPlan


# WHITELIST: Only read-only diagnostic commands are allowed
# Write operations (scale, apply, iptables) MUST have automated=False and requires_approval=True
ALLOWED_COMMANDS = {
    # Kubernetes - Read-only
    'kubectl_top_pods': 'kubectl top pods -n production',
    'kubectl_get_pods': 'kubectl get pods -n production',
    'kubectl_describe_pod': 'kubectl describe pod {pod_name} -n production',
    'kubectl_logs': 'kubectl logs {pod_name} -n production --tail=100',

    # Database - Read-only
    'pg_slow_queries': 'SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;',
    'pg_connections': 'SELECT count(*) FROM pg_stat_activity;',

    # System - Read-only
    'check_cpu': 'top -bn1 | head -20',
    'check_memory': 'free -h',
    'check_disk': 'df -h',
}

# DANGEROUS: These commands require explicit approval and are NEVER automated
RESTRICTED_COMMANDS = {
    'kubectl_scale': 'kubectl scale deployment/{deployment} --replicas={replicas} -n production',
    'kubectl_apply': 'kubectl apply -f {config_file}',
    'iptables_block': 'iptables -A INPUT -s {ip} -j DROP',
    'service_restart': 'systemctl restart {service}',
}


def validate_command(command_ref: str) -> bool:
    """
    Validate that a command reference is whitelisted

    Args:
        command_ref: Command reference (key) to validate

    Returns:
        True if allowed, False otherwise
    """
    return command_ref in ALLOWED_COMMANDS or command_ref in RESTRICTED_COMMANDS


def get_command(command_ref: str, **params) -> Optional[str]:
    """
    Get actual command from whitelist, with parameter substitution

    Args:
        command_ref: Command reference (key)
        **params: Parameters for command template

    Returns:
        Actual command string, or None if not found
    """
    if command_ref in ALLOWED_COMMANDS:
        return ALLOWED_COMMANDS[command_ref].format(**params)
    elif command_ref in RESTRICTED_COMMANDS:
        return RESTRICTED_COMMANDS[command_ref].format(**params)
    return None


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
                'command_ref': 'kubectl_top_pods',
                'command': get_command('kubectl_top_pods'),
                'automated': False,
                'requires_approval': False
            },
            {
                'step': 2,
                'action': 'Review Application Metrics',
                'description': 'Examine APM traces to identify slow operations',
                'command_ref': None,
                'command': None,
                'automated': False,
                'requires_approval': False
            },
            {
                'step': 3,
                'action': 'Check Database Performance',
                'description': 'Review slow query logs and connection pool status',
                'command_ref': 'pg_slow_queries',
                'command': get_command('pg_slow_queries'),
                'automated': False,
                'requires_approval': False
            },
            {
                'step': 4,
                'action': 'Scale Resources if Needed (MANUAL ONLY)',
                'description': 'DANGEROUS: Increase replicas ONLY after approval. Never automated.',
                'command_ref': 'kubectl_scale',
                'command': get_command('kubectl_scale', deployment='app', replicas='5'),
                'automated': False,  # NEVER automated
                'requires_approval': True  # ALWAYS requires approval
            },
            {
                'step': 5,
                'action': 'Monitor for Improvement',
                'description': 'Continue monitoring latency metrics for 15 minutes',
                'command_ref': None,
                'command': None,
                'automated': False,  # Changed to False for safety
                'requires_approval': False
            }
        ]

        return RemediationPlan(
            plan_id=f'remediation-{finding["finding_id"]}',
            finding_id=finding['finding_id'],
            title='Latency Spike Remediation',
            steps=steps,
            automated=False,  # NEVER automated
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
                'command_ref': None,
                'command': None,
                'automated': False,
                'requires_approval': False
            },
            {
                'step': 2,
                'action': 'Check Change Authorization',
                'description': 'Verify if this change was authorized and documented',
                'command_ref': None,
                'command': None,
                'automated': False,
                'requires_approval': False
            },
            {
                'step': 3,
                'action': 'Assess Security Impact',
                'description': 'Determine if drift introduces security vulnerabilities',
                'command_ref': None,
                'command': None,
                'automated': False,
                'requires_approval': False
            },
            {
                'step': 4,
                'action': 'Rollback to Baseline (MANUAL ONLY - if unauthorized)',
                'description': 'DANGEROUS: Revert to known-good configuration ONLY after approval',
                'command_ref': 'kubectl_apply',
                'command': get_command('kubectl_apply', config_file='config/baseline.yaml'),
                'automated': False,  # NEVER automated
                'requires_approval': True  # ALWAYS requires approval
            },
            {
                'step': 5,
                'action': 'Enable Config Monitoring',
                'description': 'Ensure configuration change detection is active',
                'command_ref': None,
                'command': None,
                'automated': False,  # Changed to False for safety
                'requires_approval': False
            },
            {
                'step': 6,
                'action': 'Document Change',
                'description': 'If authorized, update baseline and document the change',
                'command_ref': None,
                'command': None,
                'automated': False,
                'requires_approval': False
            }
        ]

        return RemediationPlan(
            plan_id=f'remediation-{finding["finding_id"]}',
            finding_id=finding['finding_id'],
            title='Configuration Drift Remediation',
            steps=steps,
            automated=False,  # NEVER automated
            risk_level='HIGH'
        )

    def _remediate_auth_failures(self, finding: Dict[str, Any]) -> RemediationPlan:
        """Remediation plan for authentication failures"""
        evidence = finding.get('evidence', {})
        top_ips = evidence.get('top_ips', [])

        steps = [
            {
                'step': 1,
                'action': 'Enable Rate Limiting (MANUAL ONLY)',
                'description': 'DANGEROUS: Enable aggressive rate limiting ONLY after approval',
                'command_ref': 'kubectl_apply',
                'command': get_command('kubectl_apply', config_file='config/rate-limit-strict.yaml'),
                'automated': False,  # NEVER automated
                'requires_approval': True  # ALWAYS requires approval
            },
            {
                'step': 2,
                'action': 'Block Suspicious IPs (MANUAL ONLY)',
                'description': f'DANGEROUS: Block top attacking IPs ONLY after approval: {", ".join([ip[0] for ip in top_ips[:3]])}',
                'command_ref': 'iptables_block',
                'command': get_command('iptables_block', ip=top_ips[0][0] if top_ips else "0.0.0.0"),
                'automated': False,  # NEVER automated
                'requires_approval': True  # ALWAYS requires approval
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
