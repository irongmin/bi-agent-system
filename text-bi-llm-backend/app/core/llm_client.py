# app/core/llm_client.py
import httpx
from typing import List, Dict, Optional
from app.core.config import get_settings

settings = get_settings()


class LLMClient:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def chat(self, messages: List[Dict], model: Optional[str] = None) -> str:
        # ⚠️ 기본 모델은 SQL 모델로 둠 (안 주면 SQL용으로 동작)
        use_model = model or settings.OPENAI_SQL_MODEL

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": use_model, "messages": messages}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


llm_client = LLMClient()
