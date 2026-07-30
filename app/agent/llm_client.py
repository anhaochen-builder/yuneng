"""LLM 客户端 — DeepSeek V4 Pro"""

import json
import logging
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """DeepSeek V4 Pro 客户端封装"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1,
             max_tokens: int = 4096, response_format: str = None) -> str:
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        text = self.chat(system_prompt, user_prompt, temperature, response_format="json")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    def stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.1):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=4096,
            stream=True,
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


llm = LLMClient()
