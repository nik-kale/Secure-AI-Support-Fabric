"""
Anthropic Claude LLM Provider
"""
import json
import os
import time
from typing import Dict, List, Optional, Any

from .base import LLMProvider, LLMConfig, LLMResponse, LLMError, ModelSize, RateLimitError

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """LLM provider using Anthropic's Claude"""

    MODEL_MAPPING = {
        ModelSize.SMALL: "claude-3-haiku-20240307",
        ModelSize.MEDIUM: "claude-3-sonnet-20240229",
        ModelSize.LARGE: "claude-3-opus-20240229"
    }

    def __init__(self, config: Optional[LLMConfig] = None, **kwargs):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        if config is None:
            config = LLMConfig()

        # Override with kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        super().__init__(config)

        self.client = anthropic.Anthropic(
            api_key=self.config.api_key or os.getenv('ANTHROPIC_API_KEY')
        )

    def _validate_config(self):
        """Validate Anthropic-specific configuration"""
        if not self.config.api_key and not os.getenv('ANTHROPIC_API_KEY'):
            raise ValueError(
                "Anthropic API key required. Set via config or ANTHROPIC_API_KEY env var"
            )

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Claude"""
        # Apply guardrails
        prompt = self._apply_guardrails(prompt)

        # Prepare messages
        messages = [{"role": "user", "content": prompt}]

        # Call API
        start_time = time.time()

        try:
            response = self.client.messages.create(
                model=self.get_model_name(),
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt if system_prompt else "You are a helpful assistant analyzing system telemetry.",
                messages=messages
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract content
            content = response.content[0].text

            # Validate output
            content = self._validate_output(content)

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency_ms,
                metadata={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {e}")
        except Exception as e:
            raise LLMError(f"Anthropic API error: {e}")

    async def analyze_telemetry(
        self,
        telemetry: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze telemetry using Claude

        Returns structured analysis with findings
        """
        # Limit telemetry to most recent entries
        telemetry = telemetry[-100:]  # Last 100 entries

        # Build analysis prompt
        prompt = self._build_analysis_prompt(telemetry, context)

        # Get completion
        response = await self.complete(
            prompt=prompt,
            system_prompt="""You are an expert SRE and security analyst.
Analyze the provided telemetry data for anomalies, security issues, and operational problems.
Respond in JSON format with findings."""
        )

        # Parse JSON response
        try:
            result = json.loads(response.content)
            return result
        except json.JSONDecodeError:
            # Fallback: extract structured data
            return {
                'has_findings': False,
                'analysis': response.content,
                'error': 'Failed to parse JSON response'
            }

    def _build_analysis_prompt(
        self,
        telemetry: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for telemetry analysis"""
        prompt = f"""Analyze the following telemetry data for anomalies and issues:

## Telemetry Data ({len(telemetry)} entries)

```json
{json.dumps(telemetry, indent=2)}
```
"""

        if context:
            prompt += f"""

## Additional Context

```json
{json.dumps(context, indent=2)}
```
"""

        prompt += """

## Analysis Instructions

1. Identify any anomalies or unusual patterns
2. Classify severity: CRITICAL, HIGH, MEDIUM, or LOW
3. Provide evidence from the telemetry
4. Suggest remediation steps

## Response Format

Respond in the following JSON format:

```json
{
  "has_findings": true/false,
  "findings": [
    {
      "severity": "HIGH",
      "title": "Brief title",
      "description": "Detailed description with evidence",
      "affected_services": ["service1", "service2"],
      "evidence_indices": [0, 1, 5],
      "recommendations": [
        "Step 1",
        "Step 2"
      ]
    }
  ],
  "summary": "Overall summary of telemetry health"
}
```

Provide ONLY the JSON response, no other text.
"""

        return prompt

    def get_model_name(self) -> str:
        """Get Claude model name based on size"""
        return self.MODEL_MAPPING.get(
            self.config.model_size,
            self.MODEL_MAPPING[ModelSize.MEDIUM]
        )
