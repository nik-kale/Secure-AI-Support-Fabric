"""
Local LLM Provider (Ollama, llama.cpp, etc.)
"""
from typing import Dict, List, Optional, Any
from .base import LLMProvider, LLMConfig, LLMResponse


class LocalProvider(LLMProvider):
    """Provider for local LLM inference"""

    def __init__(self, config: Optional[LLMConfig] = None, **kwargs):
        if config is None:
            config = LLMConfig()
        super().__init__(config)
        # TODO: Initialize local model connection (Ollama API, etc.)

    def _validate_config(self):
        """Validate local provider config"""
        pass  # No API key required for local

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Local completion (placeholder for now)"""
        # TODO: Implement actual local LLM inference
        return LLMResponse(
            content="[Local LLM not yet implemented]",
            model="local",
            tokens_used=0,
            latency_ms=0
        )

    async def analyze_telemetry(
        self,
        telemetry: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Local telemetry analysis"""
        # TODO: Implement with local model
        return {'has_findings': False, 'note': 'Local LLM not yet configured'}

    def get_model_name(self) -> str:
        return "local-model"
