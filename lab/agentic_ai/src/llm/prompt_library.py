"""
Versioned prompts for consistent LLM behavior
"""


class PromptLibrary:
    """Library of versioned prompts"""

    SYSTEM_PROMPTS = {
        'anomaly_detection_v1': """You are an expert SRE and security analyst.
Analyze system telemetry for anomalies, security issues, and operational problems.
Be concise but thorough. Focus on actionable insights.""",

        'remediation_planning_v1': """You are an expert SRE creating remediation plans.
Given a finding, create step-by-step remediation instructions.
Flag high-risk actions that require human approval."""
    }

    ANALYSIS_TEMPLATES = {
        'telemetry_analysis_v1': """Analyze the following telemetry data:

{telemetry}

Identify anomalies and respond in JSON format:
{{
  "has_findings": true/false,
  "findings": [
    {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "Brief title",
      "description": "Detailed description",
      "recommendations": ["action1", "action2"]
    }}
  ]
}}"""
    }

    @classmethod
    def get_system_prompt(cls, name: str) -> str:
        """Get system prompt by name"""
        return cls.SYSTEM_PROMPTS.get(name, cls.SYSTEM_PROMPTS['anomaly_detection_v1'])

    @classmethod
    def get_template(cls, name: str) -> str:
        """Get prompt template by name"""
        return cls.ANALYSIS_TEMPLATES.get(name, "")
