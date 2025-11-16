"""
Unit tests for remediation engine
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lab/agentic_ai/src'))

from remediation import RemediationEngine, RemediationPlan


class TestRemediationEngine:
    """Test suite for RemediationEngine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.engine = RemediationEngine()

    def test_generate_latency_remediation(self):
        """Should generate appropriate plan for latency issues"""
        # Given: Latency spike finding
        finding = {
            'finding_id': 'latency-123',
            'severity': 'HIGH',
            'title': 'Latency Spike Detected',
            'description': 'High latency observed'
        }

        # When: Generating plan
        plan = self.engine.generate_plan(finding)

        # Then: Plan structure is correct
        assert isinstance(plan, RemediationPlan)
        assert plan.finding_id == 'latency-123'
        assert 'Latency' in plan.title
        assert len(plan.steps) > 0

        # Check steps include investigation
        step_actions = [s['action'] for s in plan.steps]
        assert any('Investigate' in action for action in step_actions)

    def test_generate_config_drift_remediation(self):
        """Should generate plan for config drift"""
        # Given: Config drift finding
        finding = {
            'finding_id': 'config-456',
            'title': 'Configuration Drift Detected',
            'evidence': [
                {'drifts': ['debug_mode: expected=False, actual=True']}
            ]
        }

        # When: Generating plan
        plan = self.engine.generate_plan(finding)

        # Then: Plan includes rollback steps
        assert 'Config' in plan.title
        assert plan.risk_level in ['HIGH', 'MEDIUM']

        # Should have approval-required steps
        approval_steps = [s for s in plan.steps if s.get('requires_approval')]
        assert len(approval_steps) > 0

    def test_generate_auth_failure_remediation(self):
        """Should generate plan for auth failures"""
        # Given: Auth failure finding
        finding = {
            'finding_id': 'auth-789',
            'title': 'Authentication Failure Storm',
            'evidence': {
                'top_ips': [('192.168.1.100', 15), ('192.168.1.101', 10)]
            }
        }

        # When: Generating plan
        plan = self.engine.generate_plan(finding)

        # Then: Plan includes security measures
        assert 'Auth' in plan.title
        step_actions = [s['action'] for s in plan.steps]

        # Should include rate limiting
        assert any('Rate Limit' in action or 'rate' in action.lower()
                   for action in step_actions)

    def test_plan_to_dict(self):
        """Should convert plan to dictionary"""
        # Given: A remediation plan
        plan = RemediationPlan(
            plan_id='test-plan-1',
            finding_id='finding-1',
            title='Test Plan',
            steps=[
                {'step': 1, 'action': 'Do something', 'description': 'Details'}
            ],
            automated=False,
            risk_level='MEDIUM'
        )

        # When: Converting to dict
        result = plan.to_dict()

        # Then: All fields present
        assert result['plan_id'] == 'test-plan-1'
        assert result['finding_id'] == 'finding-1'
        assert result['title'] == 'Test Plan'
        assert len(result['steps']) == 1
        assert result['automated'] == False
        assert result['risk_level'] == 'MEDIUM'
        assert 'created_at' in result

    def test_approval_flagging(self):
        """Should flag high-risk actions for approval"""
        # Given: Config drift finding
        finding = {
            'finding_id': 'test-1',
            'title': 'Configuration Drift Detected'
        }

        # When: Generating plan
        plan = self.engine.generate_plan(finding)

        # Then: Rollback step requires approval
        rollback_steps = [
            s for s in plan.steps
            if 'rollback' in s.get('action', '').lower()
        ]

        if rollback_steps:
            assert rollback_steps[0].get('requires_approval') == True

    def test_generic_remediation(self):
        """Should handle unknown finding types"""
        # Given: Unknown finding type
        finding = {
            'finding_id': 'unknown-1',
            'title': 'Unknown Issue',
            'recommendations': ['Check logs', 'Restart service']
        }

        # When: Generating plan
        plan = self.engine.generate_plan(finding)

        # Then: Generic plan created with recommendations
        assert len(plan.steps) == 2
        assert plan.steps[0]['action'] == 'Check logs'
        assert plan.steps[1]['action'] == 'Restart service'


class TestRemediationSteps:
    """Test individual remediation steps"""

    def test_step_numbering(self):
        """Should number steps correctly"""
        engine = RemediationEngine()
        finding = {
            'finding_id': 'test-1',
            'title': 'Latency Spike Detected'
        }

        plan = engine.generate_plan(finding)

        # Steps should be numbered sequentially
        for i, step in enumerate(plan.steps, 1):
            assert step['step'] == i

    def test_automated_flag(self):
        """Should mark appropriate steps as automated"""
        engine = RemediationEngine()
        finding = {
            'finding_id': 'test-1',
            'title': 'Authentication Failure Storm'
        }

        plan = engine.generate_plan(finding)

        # Some steps should be automated (alerts, monitoring)
        automated_steps = [s for s in plan.steps if s.get('automated')]
        assert len(automated_steps) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
