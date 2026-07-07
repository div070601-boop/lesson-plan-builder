"""
Provider Service — AI provider abstraction layer.
Config-driven provider priority lists with automatic fallback (PRD Section 8).
"""

import httpx
from typing import Optional
from config import settings


class ProviderError(Exception):
    """Raised when all providers in the chain fail."""
    pass


class AIProvider:
    """Unified interface for a single AI provider."""

    def __init__(self, name: str, api_key: Optional[str], base_url: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.is_configured = bool(api_key)

    async def complete(self, prompt: str, system: str = "", model: str = "") -> str:
        """Send a completion request to this provider."""
        if not self.is_configured:
            raise ProviderError(f"Provider {self.name} is not configured (missing API key)")

        # Provider-specific request formatting
        if self.name == "groq":
            return await self._groq_complete(prompt, system, model or "llama-3.3-70b-versatile")
        elif self.name == "gemini":
            return await self._gemini_complete(prompt, system, model or "gemini-2.0-flash")
        elif self.name == "cerebras":
            return await self._cerebras_complete(prompt, system, model or "llama3.1-70b")
        else:
            raise ProviderError(f"Unknown provider: {self.name}")

    async def _groq_complete(self, prompt: str, system: str, model: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def _gemini_complete(self, prompt: str, system: str, model: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7},
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def _cerebras_complete(self, prompt: str, system: str, model: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


# Initialize provider instances
PROVIDERS = {
    "groq": AIProvider("groq", settings.groq_api_key, "https://api.groq.com/openai/v1"),
    "gemini": AIProvider("gemini", settings.gemini_api_key, "https://generativelanguage.googleapis.com"),
    "cerebras": AIProvider("cerebras", settings.cerebras_api_key, "https://api.cerebras.ai/v1"),
}


class ProviderService:
    """Manages the provider fallback chain."""

    async def complete(
        self,
        prompt: str,
        system: str = "",
        task_type: str = "generation",
    ) -> tuple[str, str]:
        """Run a completion through the fallback chain.
        Returns (response_text, provider_name_used)."""

        # Get priority list for this task type
        priority_map = {
            "analysis": settings.analysis_providers,
            "generation": settings.generation_providers,
            "planning": settings.planning_providers,
            "embedding": settings.embedding_providers,
        }
        providers = priority_map.get(task_type, settings.generation_providers)

        errors = []
        for provider_name in providers:
            provider = PROVIDERS.get(provider_name)
            if not provider or not provider.is_configured:
                continue

            try:
                result = await provider.complete(prompt, system)
                return result, provider_name
            except Exception as e:
                errors.append(f"{provider_name}: {str(e)}")
                continue

        raise ProviderError(
            f"All providers failed for task '{task_type}'. Errors: {'; '.join(errors)}"
        )

    def get_status(self) -> dict[str, str]:
        """Get configuration status of all providers."""
        return {
            name: "configured" if p.is_configured else "unconfigured"
            for name, p in PROVIDERS.items()
        }


provider_service = ProviderService()
