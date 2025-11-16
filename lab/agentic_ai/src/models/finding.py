"""
Shared data models for findings and remediation plans
"""
from typing import List, Dict, Any
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
