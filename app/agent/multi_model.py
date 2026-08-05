"""多模型并行诊断引擎

支持：
- deepseek-chat (V4 Pro) — 快速主模型
- deepseek-reasoner (R1) — 深度推理模型
- qwen-max — 阿里旗舰中文模型（DashScope）
- ensemble — 多模型投票融合
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class MultiModelClient:
    def __init__(self):
        self._clients: dict[str, tuple[OpenAI, str]] = {}

        if settings.deepseek_api_key and settings.deepseek_api_key != "your_api_key_here":
            self._clients["deepseek-chat"] = (
                OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url),
                settings.deepseek_model,
            )
            self._clients["deepseek-reasoner"] = (
                OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url),
                settings.deepseek_reasoner_model,
            )

        if settings.dashscope_api_key:
            self._clients["qwen-max"] = (
                OpenAI(api_key=settings.dashscope_api_key, base_url=settings.qwen_base_url),
                settings.qwen_model,
            )

        self._available = list(self._clients.keys())
        logger.info(f"多模型引擎就绪: {self._available}")

    def diagnose_multi(
        self, system_prompt: str, user_prompt: str, models: list[str] = None
    ) -> dict[str, Any]:
        models = models or self._available[:2]
        models = [m for m in models if m in self._clients]

        if not models:
            return {"report_text": "无可用模型", "confidence": 0.0, "root_cause": "", "risk_level": "UNKNOWN", "models_count": 0}

        with ThreadPoolExecutor(max_workers=len(models)) as pool:
            futures = {
                pool.submit(self._call_and_parse, m, system_prompt, user_prompt): m
                for m in models
            }
            results = {}
            for future in futures:
                model = futures[future]
                try:
                    results[model] = self._call_and_parse(model, system_prompt, user_prompt)
                except Exception as e:
                    logger.warning(f"模型 {model} 调用失败: {e}")
                    results[model] = None

        return self._ensemble(results)

    def _call_and_parse(self, model: str, system: str, user: str) -> dict:
        text = self._call_model(model, system, user)
        return self._parse_single(text, model)

    def diagnose_single(self, system_prompt: str, user_prompt: str, model: str = None) -> dict[str, Any]:
        model = model or self._available[0] if self._available else None

        if model and model in self._clients:
            try:
                return self._call_and_parse(model, system_prompt, user_prompt)
            except Exception as e:
                logger.warning(f"在线模型 {model} 调用失败: {e}，尝试降级")

        from app.agent.llm_provider import hybrid_llm
        text = hybrid_llm.chat(system_prompt, user_prompt)
        mode = hybrid_llm.current_mode
        parsed = {"root_cause": "", "confidence": 0.5, "risk_level": "MEDIUM"}
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                parsed.update(json.loads(json_str))
            elif text.strip().startswith("{"):
                parsed.update(json.loads(text.strip()))
        except (json.JSONDecodeError, IndexError):
            pass
        return {"report_text": text, **parsed, "model": f"fallback-{mode}"}

    @property
    def mode_status(self) -> dict:
        from app.agent.llm_provider import hybrid_llm
        return hybrid_llm.mode_status()

    def _call_model(self, model: str, system: str, user: str) -> str:
        client, model_id = self._clients[model]

        kwargs = dict(
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=2048,
        )

        if "reasoner" in model or "r1" in model:
            del kwargs["temperature"]
            kwargs["max_tokens"] = 2048

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _parse_single(self, text: str, model: str) -> dict[str, Any]:
        parsed = {"root_cause": "", "confidence": 0.5, "risk_level": "MEDIUM", "self_score": 60}
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                parsed.update(json.loads(json_str))
            elif text.strip().startswith("{"):
                parsed.update(json.loads(text.strip()))
        except (json.JSONDecodeError, IndexError):
            pass

        return {"report_text": text, **parsed, "model": model}

    def _ensemble(self, results: dict[str, dict]) -> dict[str, Any]:
        valid = {m: r for m, r in results.items() if r and r.get("report_text")}
        count = len(valid)

        if count == 0:
            return {"report_text": "所有模型调用失败", "confidence": 0.0, "root_cause": "", "risk_level": "UNKNOWN", "models_count": 0}
        if count == 1:
            m, r = next(iter(valid.items()))
            r["models_count"] = 1
            r["models_used"] = [m]
            return r

        scores = [r.get("confidence", 0.5) for r in valid.values()]
        avg_confidence = sum(scores) / len(scores)

        agree_count = sum(
            1 for s in scores
            if abs(s - avg_confidence) < 0.3 or s > 0.6
        )
        agreement_bonus = 0.10 if agree_count >= 2 else 0.0
        ensemble_confidence = min(avg_confidence + agreement_bonus, 0.95)

        causes = [r.get("root_cause", "") for r in valid.values() if r.get("root_cause")]
        cause = causes[0] if causes else "多模型未达成统一根因"

        reports = []
        for m, r in valid.items():
            reports.append(f"## [{m}] 诊断结果\n{r.get('report_text', '')[:1500]}")
        ensemble_report = f"## 多模型联合诊断 (置信度 {ensemble_confidence*100:.0f}%)\n\n"
        ensemble_report += f"参与模型: {', '.join(list(valid.keys()))}\n"
        ensemble_report += f"模型共识度: {agree_count}/{count}\n"
        ensemble_report += f"综合根因: {cause}\n\n"
        ensemble_report += "\n\n---\n\n".join(reports)

        return {
            "report_text": ensemble_report,
            "confidence": ensemble_confidence,
            "root_cause": cause,
            "risk_level": max(
                (r.get("risk_level", "MEDIUM") for r in valid.values()),
                key=lambda x: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(x, 0),
            ),
            "models_count": count,
            "models_used": list(valid.keys()),
            "ensemble": True,
        }


multi_client = MultiModelClient()
