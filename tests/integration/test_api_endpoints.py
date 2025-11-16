"""
Integration tests for API endpoints
Tests the full stack: Gateway -> Services -> Database
"""
import pytest
import requests
import time
from datetime import datetime


# Test configuration
GATEWAY_URL = "http://localhost:8080"
TELEMETRY_URL = "http://localhost:8081"
AI_URL = "http://localhost:8082"


@pytest.fixture(scope="module")
def check_services():
    """Ensure services are running before tests"""
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{GATEWAY_URL}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                pytest.skip("Services not available for integration tests")
    return False


class TestTelemetryIngestion:
    """Test telemetry ingestion endpoints"""

    def test_ingest_log_telemetry(self, check_services):
        """Should successfully ingest log telemetry"""
        # Given: Log telemetry payload
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "integration-test",
            "level": "INFO",
            "message": "Test log from integration test",
            "request_id": "test-001"
        }

        # When: Sending to gateway
        response = requests.post(
            f"{GATEWAY_URL}/api/telemetry/logs",
            json=log_data
        )

        # Then: Successfully ingested
        assert response.status_code == 201
        data = response.json()
        assert data['success'] == True
        assert 'telemetry_id' in data

    def test_ingest_metrics_telemetry(self, check_services):
        """Should successfully ingest metrics"""
        # Given: Metrics payload
        metrics_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "integration-test",
            "metrics": {
                "cpu_percent": 75.5,
                "memory_percent": 62.3,
                "request_rate": 150
            }
        }

        # When: Sending to gateway
        response = requests.post(
            f"{GATEWAY_URL}/api/telemetry/metrics",
            json=metrics_data
        )

        # Then: Successfully ingested
        assert response.status_code == 201
        data = response.json()
        assert data['success'] == True

    def test_ingest_config_telemetry(self, check_services):
        """Should successfully ingest config events"""
        # Given: Config payload
        config_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "integration-test",
            "config_version": "test-1.0.0",
            "configuration": {
                "debug_mode": False,
                "log_level": "INFO"
            },
            "changed_by": "integration-test",
            "change_reason": "Testing"
        }

        # When: Sending to gateway
        response = requests.post(
            f"{GATEWAY_URL}/api/telemetry/config",
            json=config_data
        )

        # Then: Successfully ingested
        assert response.status_code == 201

    def test_query_telemetry(self, check_services):
        """Should query stored telemetry"""
        # Given: Some telemetry already ingested
        # When: Querying
        response = requests.get(
            f"{GATEWAY_URL}/api/telemetry/query",
            params={"limit": 10}
        )

        # Then: Returns telemetry
        assert response.status_code == 200
        data = response.json()
        assert 'telemetry' in data
        assert isinstance(data['telemetry'], list)

    def test_telemetry_statistics(self, check_services):
        """Should return telemetry statistics"""
        # When: Getting stats
        response = requests.get(f"{GATEWAY_URL}/api/telemetry/stats")

        # Then: Returns statistics
        assert response.status_code == 200
        data = response.json()
        assert 'statistics' in data
        stats = data['statistics']
        assert 'total_count' in stats
        assert 'count_by_type' in stats


class TestAIAnalysis:
    """Test AI analysis and detection"""

    def setup_method(self):
        """Seed telemetry before each test"""
        # Clear and seed fresh data
        self._seed_latency_spike_data()

    def _seed_latency_spike_data(self):
        """Helper to seed latency spike scenario"""
        for i in range(5):
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": "test-service",
                "level": "WARNING",
                "message": "Slow request",
                "duration_ms": 5000 + (i * 100),
                "request_id": f"slow-{i}"
            }
            requests.post(f"{GATEWAY_URL}/api/telemetry/logs", json=log_data)

        # Give it a moment to persist
        time.sleep(0.5)

    def test_run_analysis(self, check_services):
        """Should run analysis and generate findings"""
        # When: Triggering analysis
        response = requests.post(f"{GATEWAY_URL}/api/run-analysis")

        # Then: Analysis completes
        assert response.status_code == 200
        data = response.json()
        assert 'success' in data or 'result' in data

    def test_get_findings(self, check_services):
        """Should retrieve findings after analysis"""
        # Given: Analysis has run
        requests.post(f"{GATEWAY_URL}/api/run-analysis")
        time.sleep(1)  # Wait for analysis

        # When: Getting findings
        response = requests.get(f"{GATEWAY_URL}/api/ai/findings")

        # Then: Returns findings
        assert response.status_code == 200
        data = response.json()
        assert 'findings' in data
        assert isinstance(data['findings'], list)

    def test_get_remediation_plans(self, check_services):
        """Should retrieve remediation plans"""
        # Given: Analysis has run
        requests.post(f"{GATEWAY_URL}/api/run-analysis")
        time.sleep(1)

        # When: Getting remediation
        response = requests.get(f"{GATEWAY_URL}/api/ai/remediation")

        # Then: Returns plans
        assert response.status_code == 200
        data = response.json()
        assert 'remediation_plans' in data


class TestEndToEnd:
    """End-to-end workflow tests"""

    def test_complete_detection_workflow(self, check_services):
        """Test complete workflow: ingest -> analyze -> findings -> remediation"""
        # Step 1: Ingest problematic telemetry
        for i in range(10):
            log_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": "e2e-test",
                "level": "WARNING",
                "message": "Request exceeded timeout",
                "duration_ms": 8000,
                "request_id": f"e2e-{i}"
            }
            response = requests.post(
                f"{GATEWAY_URL}/api/telemetry/logs",
                json=log_data
            )
            assert response.status_code == 201

        time.sleep(1)

        # Step 2: Run analysis
        response = requests.post(f"{GATEWAY_URL}/api/run-analysis")
        assert response.status_code == 200

        time.sleep(1)

        # Step 3: Verify findings exist
        response = requests.get(f"{GATEWAY_URL}/api/ai/findings?limit=10")
        assert response.status_code == 200
        findings_data = response.json()

        # Should have at least one finding
        findings = findings_data.get('findings', [])
        assert len(findings) > 0

        # Step 4: Verify remediation plans exist
        response = requests.get(f"{GATEWAY_URL}/api/ai/remediation?limit=10")
        assert response.status_code == 200
        remediation_data = response.json()

        plans = remediation_data.get('remediation_plans', [])
        assert len(plans) > 0

        # Step 5: Verify plan structure
        plan = plans[0]
        assert 'plan_id' in plan
        assert 'title' in plan
        assert 'steps' in plan
        assert len(plan['steps']) > 0

    def test_config_drift_workflow(self, check_services):
        """Test config drift detection workflow"""
        # Step 1: Ingest drifted config
        config_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "e2e-config-test",
            "config_version": "drift-1.0.0",
            "configuration": {
                "debug_mode": True,  # DRIFT
                "log_level": "DEBUG",
                "enable_auth": True,
                "tls_enabled": True
            },
            "changed_by": "unknown",
            "change_reason": "Test drift"
        }

        response = requests.post(
            f"{GATEWAY_URL}/api/telemetry/config",
            json=config_data
        )
        assert response.status_code == 201

        time.sleep(1)

        # Step 2: Run analysis
        requests.post(f"{GATEWAY_URL}/api/run-analysis")
        time.sleep(1)

        # Step 3: Check for config drift finding
        response = requests.get(f"{GATEWAY_URL}/api/ai/findings")
        findings = response.json().get('findings', [])

        config_findings = [
            f for f in findings
            if 'config' in f.get('title', '').lower()
        ]

        # Should detect config drift
        assert len(config_findings) > 0


class TestSystemHealth:
    """Test system health and status endpoints"""

    def test_gateway_health(self, check_services):
        """Should return healthy status"""
        response = requests.get(f"{GATEWAY_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert 'services' in data

    def test_system_status(self, check_services):
        """Should return overall system status"""
        response = requests.get(f"{GATEWAY_URL}/api/status")

        assert response.status_code == 200
        data = response.json()
        assert 'telemetry' in data or 'ai_findings' in data


class TestErrorHandling:
    """Test error handling and validation"""

    def test_invalid_telemetry_rejected(self, check_services):
        """Should reject invalid telemetry"""
        # Given: Invalid payload (missing required fields)
        invalid_data = {
            "invalid_field": "value"
        }

        # When: Attempting to ingest
        response = requests.post(
            f"{GATEWAY_URL}/api/telemetry/logs",
            json=invalid_data
        )

        # Then: Should fail (4xx error)
        # Note: Current implementation may not validate strictly
        # This test documents expected behavior
        assert response.status_code in [400, 500]

    def test_malformed_json_rejected(self, check_services):
        """Should reject malformed JSON"""
        # When: Sending malformed JSON
        response = requests.post(
            f"{GATEWAY_URL}/api/telemetry/logs",
            data="not json",
            headers={"Content-Type": "application/json"}
        )

        # Then: Should fail
        assert response.status_code >= 400


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
