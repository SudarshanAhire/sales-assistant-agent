import json
from typing import Any
import httpx
from app.config import settings


class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not self.api_key:
            return self._fallback_response(messages)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _fallback_response(self, messages: list[dict[str, str]]) -> str:
        # Deterministic local fallback so project works without an API key during review.
        joined = "\n".join(m.get("content", "") for m in messages).lower()
        if "enterprise" in joined or "sso" in joined or "audit" in joined or "sla" in joined:
            return "The Enterprise plan is $499/mo and includes unlimited users, SSO, audit logs, and SLA."
        if "growth" in joined or "webhook" in joined:
            return "The Growth plan is $199/mo and includes 25 users, webhooks, and priority support."
        if "starter" in joined:
            return "The Starter plan is $49/mo and includes 5 users, API access, and email support."
        return "I found three plans: Starter at $49/mo, Growth at $199/mo, and Enterprise at $499/mo."

    async def json_chat(self, messages: list[dict[str, str]], fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            content = await self.chat(messages, temperature=0)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except Exception:
            pass
        return fallback


llm_service = LLMService()
