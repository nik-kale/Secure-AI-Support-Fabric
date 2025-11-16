"""Guardrails for LLM input/output safety"""

class InputGuardrail:
    """Validate and sanitize LLM inputs"""

    @staticmethod
    def validate(prompt: str, max_length: int = 50000) -> str:
        """Validate and sanitize input prompt"""
        if len(prompt) > max_length:
            prompt = prompt[:max_length] + "\n[Truncated]"
        return prompt


class OutputGuardrail:
    """Validate LLM outputs"""

    @staticmethod
    def validate(response: str) -> str:
        """Validate LLM response"""
        # TODO: Add content filtering, PII detection, etc.
        return response
