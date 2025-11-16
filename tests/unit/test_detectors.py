"""
Unit tests for anomaly detectors
"""
import pytest
from datetime import datetime
import sys
import os

# Add lab modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lab/agentic_ai/src'))

from detectors import (
    LatencySpikeDetector,
    ConfigDriftDetector,
    AuthFailureDetector,
    AnomalyDetectorEngine
)


class TestLatencySpikeDetector:
    """Test suite for LatencySpikeDetector"""

    def setup_method(self):
        """Setup test fixtures"""
        self.detector = LatencySpikeDetector(threshold_ms=1000, min_occurrences=3)

    def test_detect_latency_spike_above_threshold(self):
        """Should detect when multiple requests exceed threshold"""
        # Given: Telemetry with slow requests
        telemetry = [
            {
                'telemetry_type': 'log',
                'data': {
                    'duration_ms': 5000,
                    'request_id': f'req-{i}'
                }
            }
            for i in range(5)
        ]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: Finding should be generated
        assert finding is not None
        assert finding.severity == 'HIGH'
        assert 'Latency Spike' in finding.title
        assert len(finding.evidence) >= 3

    def test_no_detection_below_threshold(self):
        """Should not detect when requests are fast"""
        # Given: Fast requests
        telemetry = [
            {
                'telemetry_type': 'log',
                'data': {'duration_ms': 100}
            }
            for _ in range(5)
        ]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: No finding
        assert finding is None

    def test_insufficient_occurrences(self):
        """Should not detect with too few slow requests"""
        # Given: Only 2 slow requests (below min_occurrences=3)
        telemetry = [
            {'telemetry_type': 'log', 'data': {'duration_ms': 5000}},
            {'telemetry_type': 'log', 'data': {'duration_ms': 5000}},
        ]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: No finding
        assert finding is None

    def test_custom_threshold(self):
        """Should respect custom threshold values"""
        # Given: Custom detector with high threshold
        detector = LatencySpikeDetector(threshold_ms=10000, min_occurrences=2)
        telemetry = [
            {'telemetry_type': 'log', 'data': {'duration_ms': 15000}},
            {'telemetry_type': 'log', 'data': {'duration_ms': 12000}},
        ]

        # When: Running detector
        finding = detector.analyze(telemetry)

        # Then: Finding generated
        assert finding is not None


class TestConfigDriftDetector:
    """Test suite for ConfigDriftDetector"""

    def setup_method(self):
        """Setup test fixtures"""
        self.baseline = {
            'debug_mode': False,
            'log_level': 'INFO',
            'enable_auth': True,
            'tls_enabled': True
        }
        self.detector = ConfigDriftDetector(baseline_config=self.baseline)

    def test_detect_debug_mode_drift(self):
        """Should detect when debug mode is enabled"""
        # Given: Config with debug enabled
        telemetry = [{
            'telemetry_type': 'config',
            'data': {
                'timestamp': datetime.utcnow().isoformat(),
                'configuration': {
                    'debug_mode': True,  # DRIFT
                    'log_level': 'DEBUG',
                    'enable_auth': True,
                    'tls_enabled': True
                }
            }
        }]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: Finding generated
        assert finding is not None
        assert 'Configuration Drift' in finding.title
        assert finding.severity in ['CRITICAL', 'MEDIUM']

    def test_detect_security_drift(self):
        """Should detect critical security config changes"""
        # Given: Auth disabled (critical security issue)
        telemetry = [{
            'telemetry_type': 'config',
            'data': {
                'configuration': {
                    'debug_mode': False,
                    'log_level': 'INFO',
                    'enable_auth': False,  # CRITICAL DRIFT
                    'tls_enabled': False   # CRITICAL DRIFT
                }
            }
        }]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: Critical severity for auth/TLS changes
        assert finding is not None
        assert finding.severity == 'CRITICAL'

    def test_no_drift_with_baseline(self):
        """Should not detect when config matches baseline"""
        # Given: Config matching baseline
        telemetry = [{
            'telemetry_type': 'config',
            'data': {
                'configuration': self.baseline.copy()
            }
        }]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: No finding
        assert finding is None


class TestAuthFailureDetector:
    """Test suite for AuthFailureDetector"""

    def setup_method(self):
        """Setup test fixtures"""
        self.detector = AuthFailureDetector(threshold=10)

    def test_detect_auth_failure_storm(self):
        """Should detect multiple authentication failures"""
        # Given: Many auth failures
        telemetry = [
            {
                'telemetry_type': 'log',
                'data': {
                    'level': 'ERROR',
                    'message': 'Authentication failed',
                    'user': f'user_{i % 3}',
                    'source_ip': f'192.168.1.{i % 2}'
                }
            }
            for i in range(20)
        ]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: Finding generated
        assert finding is not None
        assert finding.severity == 'HIGH'
        assert 'Authentication Failure' in finding.title

        # Check evidence structure
        evidence = finding.evidence
        assert isinstance(evidence, dict)
        assert evidence['total_failures'] >= 10
        assert 'top_users' in evidence
        assert 'top_ips' in evidence

    def test_below_threshold(self):
        """Should not detect below threshold"""
        # Given: Few auth failures
        telemetry = [
            {
                'telemetry_type': 'log',
                'data': {
                    'level': 'ERROR',
                    'message': 'Authentication failed'
                }
            }
            for _ in range(5)  # Below threshold of 10
        ]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: No finding
        assert finding is None

    def test_groups_by_user_and_ip(self):
        """Should group failures by user and IP"""
        # Given: Failures from specific users/IPs
        telemetry = [
            {
                'telemetry_type': 'log',
                'data': {
                    'level': 'ERROR',
                    'message': 'Authentication failed',
                    'user': 'attacker',
                    'source_ip': '10.0.0.1'
                }
            }
            for _ in range(15)
        ]

        # When: Running detector
        finding = self.detector.analyze(telemetry)

        # Then: Evidence includes groupings
        evidence = finding.evidence
        assert len(evidence['top_users']) > 0
        assert len(evidence['top_ips']) > 0

        # Top attacker should be identified
        top_user = evidence['top_users'][0]
        assert top_user[0] == 'attacker'
        assert top_user[1] == 15


class TestAnomalyDetectorEngine:
    """Test suite for main detection engine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.engine = AnomalyDetectorEngine()

    def test_runs_all_detectors(self):
        """Should run all registered detectors"""
        # Given: Mixed telemetry triggering multiple detectors
        telemetry = [
            # Slow requests (latency detector)
            {
                'telemetry_type': 'log',
                'data': {'duration_ms': 5000}
            }
            for _ in range(5)
        ] + [
            # Auth failures (auth detector)
            {
                'telemetry_type': 'log',
                'data': {
                    'level': 'ERROR',
                    'message': 'Authentication failed'
                }
            }
            for _ in range(15)
        ]

        # When: Running engine
        findings = self.engine.analyze_telemetry(telemetry)

        # Then: Multiple findings
        assert len(findings) >= 1
        assert all(hasattr(f, 'severity') for f in findings)
        assert all(hasattr(f, 'recommendations') for f in findings)

    def test_empty_telemetry(self):
        """Should handle empty telemetry gracefully"""
        # When: Empty telemetry
        findings = self.engine.analyze_telemetry([])

        # Then: No findings, no errors
        assert findings == []

    def test_malformed_telemetry(self):
        """Should handle malformed data gracefully"""
        # Given: Malformed telemetry
        telemetry = [
            {'invalid': 'structure'},
            None,
            {'telemetry_type': 'log'}  # Missing data
        ]

        # When: Running engine (should not crash)
        findings = self.engine.analyze_telemetry(telemetry)

        # Then: No crash, possibly no findings
        assert isinstance(findings, list)


class TestFindingObject:
    """Test Finding data structure"""

    def test_finding_to_dict(self):
        """Should convert finding to dictionary"""
        from detectors import Finding

        # Given: A finding
        finding = Finding(
            finding_id='test-123',
            severity='HIGH',
            title='Test Finding',
            description='Test description',
            evidence=[{'key': 'value'}],
            recommendations=['Fix this', 'Then that']
        )

        # When: Converting to dict
        result = finding.to_dict()

        # Then: All fields present
        assert result['finding_id'] == 'test-123'
        assert result['severity'] == 'HIGH'
        assert result['title'] == 'Test Finding'
        assert result['description'] == 'Test description'
        assert len(result['evidence']) == 1
        assert len(result['recommendations']) == 2
        assert 'detected_at' in result


# Pytest configuration
@pytest.fixture
def sample_log_telemetry():
    """Fixture for sample log telemetry"""
    return [
        {
            'telemetry_type': 'log',
            'data': {
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'test-service',
                'level': 'INFO',
                'message': 'Test message',
                'duration_ms': 100
            }
        }
    ]


@pytest.fixture
def sample_metric_telemetry():
    """Fixture for sample metric telemetry"""
    return [
        {
            'telemetry_type': 'metric',
            'data': {
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'test-service',
                'metrics': {
                    'cpu_percent': 45.5,
                    'memory_percent': 52.3
                }
            }
        }
    ]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=detectors'])
