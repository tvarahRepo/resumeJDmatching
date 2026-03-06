from __future__ import annotations

import os
import httpx
from typing import Any, Dict, List
from .settings import load_settings


class OpenRouterClient:
    def __init__(self):
        s = load_settings()
        self.base_url = s.openrouter_base_url.rstrip("/")
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set in environment/.env")
        self.timeout = httpx.Timeout(90.0)

    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]