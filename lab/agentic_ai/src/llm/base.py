"""
Base LLM Provider interface
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class ModelSize(Enum):
    """Model size/capability tiers"""
    SMALL = "small"      # Fast, cheap, simple tasks
    MEDIUM = "medium"    # Balanced performance
    LARGE = "large"      # Most capable, expensive


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    api_key: Optional[str] = None
    model_size: ModelSize = ModelSize.MEDIUM
    max_tokens: int = 1024
    temperature: float = 0.7
    timeout: int = 30
    enable_guardrails: bool = True
    cache_responses: bool = True


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    tokens_used: int
    latency_ms: float
    cached: bool = False
    metadata: Dict[str, Any] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self):
        """Validate provider-specific configuration"""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from prompt

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def analyze_telemetry(
        self,
        telemetry: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze telemetry data for anomalies

        Args:
            telemetry: List of telemetry entries
            context: Additional context (e.g., previous findings)

        Returns:
            Analysis result with findings
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the actual model name being used"""
        pass

    def _apply_guardrails(self, prompt: str) -> str:
        """Apply input guardrails to prompt"""
        if not self.config.enable_guardrails:
            return prompt

        # Basic guardrail: limit prompt size
        max_chars = 50000
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n\n[Truncated...]"

        return prompt

    def _validate_output(self, response: str) -> str:
        """Apply output guardrails"""
        if not self.config.enable_guardrails:
            return response

        # Basic validation: check for harmful content
        # In production, use more sophisticated checks
        return response


class LLMError(Exception):
    """Base exception for LLM operations"""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded"""
    pass


class InvalidResponseError(LLMError):
    """Invalid response from LLM"""
    pass
