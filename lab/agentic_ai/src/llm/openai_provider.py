"""
OpenAI GPT LLM Provider
"""
import json
import os
import time
from typing import Dict, List, Optional, Any

from .base import LLMProvider, LLMConfig, LLMResponse, LLMError, ModelSize, RateLimitError

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(LLMProvider):
    """LLM provider using OpenAI's GPT models"""

    MODEL_MAPPING = {
        ModelSize.SMALL: "gpt-3.5-turbo",
        ModelSize.MEDIUM: "gpt-4-turbo-preview",
        ModelSize.LARGE: "gpt-4"
    }

    def __init__(self, config: Optional[LLMConfig] = None, **kwargs):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Install with: pip install openai")

        if config is None:
            config = LLMConfig()

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        super().__init__(config)

        self.client = openai.OpenAI(
            api_key=self.config.api_key or os.getenv('OPENAI_API_KEY')
        )

    def _validate_config(self):
        """Validate OpenAI configuration"""
        if not self.config.api_key and not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OpenAI API key required")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using GPT"""
        prompt = self._apply_guardrails(prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.get_model_name(),
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )

            latency_ms = (time.time() - start_time) * 1000

            content = response.choices[0].message.content
            content = self._validate_output(content)

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.total_tokens,
                latency_ms=latency_ms,
                metadata={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            )

        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit: {e}")
        except Exception as e:
            raise LLMError(f"OpenAI API error: {e}")

    async def analyze_telemetry(
        self,
        telemetry: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze telemetry using GPT"""
        telemetry = telemetry[-100:]

        prompt = f"""Analyze this telemetry for anomalies:

{json.dumps(telemetry, indent=2)}

Respond in JSON format:
{{
  "has_findings": true/false,
  "findings": [
    {{
      "severity": "HIGH",
      "title": "Issue title",
      "description": "Details",
      "recommendations": ["Fix 1", "Fix 2"]
    }}
  ]
}}
"""

        response = await self.complete(
            prompt=prompt,
            system_prompt="You are an SRE analyzing system telemetry. Respond only with JSON."
        )

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {'has_findings': False, 'error': 'Invalid JSON response'}

    def get_model_name(self) -> str:
        """Get GPT model name"""
        return self.MODEL_MAPPING.get(self.config.model_size, self.MODEL_MAPPING[ModelSize.MEDIUM])
