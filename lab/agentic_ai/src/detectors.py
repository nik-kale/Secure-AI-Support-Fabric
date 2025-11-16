"""
Detection rules and logic for identifying anomalies in telemetry data
This is a simplified, rule-based "agentic" system for lab purposes
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

class Finding:
    """Represents a detected issue"""

    def __init__(
        self,
        finding_id: str,
        severity: str,
        title: str,
        description: str,
        evidence: List[Dict[str, Any]],
        recommendations: List[str]
    ):
        self.finding_id = finding_id
        self.severity = severity
        self.title = title
        self.description = description
        self.evidence = evidence
        self.recommendations = recommendations
        self.detected_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary"""
        return {
            'finding_id': self.finding_id,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'evidence': self.evidence,
            'recommendations': self.recommendations,
            'detected_at': self.detected_at
        }


class LatencySpikeDetector:
    """Detect latency spikes in log data"""

    def __init__(self, threshold_ms: int = 1000, min_occurrences: int = 3):
        self.threshold_ms = threshold_ms
        self.min_occurrences = min_occurrences

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze telemetry for latency spikes"""
        slow_requests = []

        for entry in telemetry:
            if entry.get('telemetry_type') == 'log':
                data = entry.get('data', {})
                duration = data.get('duration_ms', 0)

                if duration > self.threshold_ms:
                    slow_requests.append(data)

        if len(slow_requests) >= self.min_occurrences:
            avg_duration = sum(r.get('duration_ms', 0) for r in slow_requests) / len(slow_requests)

            return Finding(
                finding_id=f'latency-spike-{datetime.utcnow().timestamp()}',
                severity='HIGH',
                title='Latency Spike Detected',
                description=f'Detected {len(slow_requests)} requests exceeding {self.threshold_ms}ms threshold. Average duration: {avg_duration:.0f}ms.',
                evidence=slow_requests[:5],  # First 5 examples
                recommendations=[
                    'Check application performance metrics',
                    'Review database query performance',
                    'Investigate external service dependencies',
                    'Consider scaling resources if sustained high load'
                ]
            )

        return None


class ConfigDriftDetector:
    """Detect configuration drift from baseline"""

    def __init__(self, baseline_config: Optional[Dict[str, Any]] = None):
        self.baseline_config = baseline_config or {
            'debug_mode': False,
            'log_level': 'INFO',
            'enable_auth': True,
            'tls_enabled': True
        }

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze telemetry for config drift"""
        config_changes = []

        for entry in telemetry:
            if entry.get('telemetry_type') == 'config':
                data = entry.get('data', {})
                current_config = data.get('configuration', {})

                drifts = self._detect_drift(current_config)
                if drifts:
                    config_changes.append({
                        'timestamp': data.get('timestamp'),
                        'drifts': drifts,
                        'changed_by': data.get('changed_by', 'unknown')
                    })

        if config_changes:
            all_drifts = []
            for change in config_changes:
                all_drifts.extend(change['drifts'])

            return Finding(
                finding_id=f'config-drift-{datetime.utcnow().timestamp()}',
                severity='CRITICAL' if any('auth' in d or 'tls' in d for d in all_drifts) else 'MEDIUM',
                title='Configuration Drift Detected',
                description=f'Detected {len(all_drifts)} configuration drift(s) from baseline. This may indicate unauthorized changes or misconfigurations.',
                evidence=config_changes,
                recommendations=[
                    'Review recent configuration changes',
                    'Verify change authorization and approval',
                    'Consider rolling back to known-good configuration',
                    'Enable configuration change monitoring and alerts',
                    'Implement infrastructure-as-code for config management'
                ]
            )

        return None

    def _detect_drift(self, current_config: Dict[str, Any]) -> List[str]:
        """Compare current config against baseline"""
        drifts = []

        for key, baseline_value in self.baseline_config.items():
            current_value = current_config.get(key)

            if current_value != baseline_value:
                drifts.append(
                    f'{key}: expected={baseline_value}, actual={current_value}'
                )

        return drifts


class AuthFailureDetector:
    """Detect authentication failure storms"""

    def __init__(self, threshold: int = 10, time_window_seconds: int = 60):
        self.threshold = threshold
        self.time_window_seconds = time_window_seconds

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze telemetry for auth failures"""
        auth_failures = []

        for entry in telemetry:
            if entry.get('telemetry_type') == 'log':
                data = entry.get('data', {})

                if 'auth' in data.get('message', '').lower() and data.get('level') == 'ERROR':
                    auth_failures.append(data)

        if len(auth_failures) >= self.threshold:
            # Group by user or IP
            by_user = {}
            by_ip = {}

            for failure in auth_failures:
                user = failure.get('user', 'unknown')
                ip = failure.get('source_ip', 'unknown')

                by_user[user] = by_user.get(user, 0) + 1
                by_ip[ip] = by_ip.get(ip, 0) + 1

            return Finding(
                finding_id=f'auth-failure-storm-{datetime.utcnow().timestamp()}',
                severity='HIGH',
                title='Authentication Failure Storm Detected',
                description=f'Detected {len(auth_failures)} authentication failures. This may indicate a brute-force attack or credential stuffing attempt.',
                evidence={
                    'total_failures': len(auth_failures),
                    'unique_users': len(by_user),
                    'unique_ips': len(by_ip),
                    'top_users': sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5],
                    'top_ips': sorted(by_ip.items(), key=lambda x: x[1], reverse=True)[:5],
                    'sample_failures': auth_failures[:3]
                },
                recommendations=[
                    'Enable rate limiting on authentication endpoints',
                    'Consider implementing account lockout policies',
                    'Review and block suspicious IP addresses',
                    'Enable MFA for affected accounts',
                    'Monitor for credential stuffing patterns',
                    'Alert security team for investigation'
                ]
            )

        return None


class AnomalyDetectorEngine:
    """Main detection engine coordinating multiple detectors"""

    def __init__(self):
        self.detectors = [
            LatencySpikeDetector(threshold_ms=1000, min_occurrences=3),
            ConfigDriftDetector(),
            AuthFailureDetector(threshold=10)
        ]

    def analyze_telemetry(self, telemetry: List[Dict[str, Any]]) -> List[Finding]:
        """Run all detectors on telemetry data"""
        findings = []

        for detector in self.detectors:
            finding = detector.analyze(telemetry)
            if finding:
                findings.append(finding)

        return findings
