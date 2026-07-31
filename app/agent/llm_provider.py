"""混合部署 LLM Provider — 三模自动切换

层级策略:
  L1 (主)  → DeepSeek API (在线, 最快最准)
  L2 (降1) → Qwen GGUF 本地推理 (离线, CPU)
  L3 (降2) → 规则引擎 (纯离线, 无LLM)

切换触发:
  - L1→L2: DeepSeek API 不可用(网络超时/401/500)
  - L2→L1: 定时探测 DeepSeek API 恢复
  - L2→L3: Qwen GGUF 模型加载失败
  - L3→L2: 系统闲置时尝试加载 GGUF

所有 Provider 实现统一接口: chat(), chat_json(), stream(), health_check()
"""

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        ...

    def chat_json(self, system_prompt: str, user_prompt: str,
                  temperature: float = 0.1) -> dict:
        text = self.chat(system_prompt, user_prompt, temperature, max_tokens=1024)
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {"raw": text}

    @abstractmethod
    def health_check(self) -> bool:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class DeepSeekProvider(BaseLLMProvider):
    """L1: DeepSeek API — 在线模式"""

    provider_name = "deepseek"

    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        from openai import OpenAI
        key = settings.deepseek_api_key
        if not key or key == "your_api_key_here":
            logger.warning("DeepSeek API Key 未配置")
            return
        try:
            self._client = OpenAI(api_key=key, base_url=settings.deepseek_base_url)
            self._available = True
            logger.info("DeepSeek Provider 就绪")
        except Exception as e:
            logger.warning(f"DeepSeek 初始化失败: {e}")

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        if not self._client:
            raise RuntimeError("DeepSeek 客户端未初始化")
        response = self._client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.models.list()
            return True
        except Exception:
            self._available = False
            return False

    def is_available(self) -> bool:
        return self._available and self.health_check()


class QwenLocalProvider(BaseLLMProvider):
    """L2: Qwen GGUF 本地 CPU 推理"""

    provider_name = "qwen-local"

    def __init__(self):
        self._model = None
        self._available = False
        self._model_path = settings.qwen_local_path
        self._init_model()

    def _init_model(self):
        if not self._model_path or not os.path.exists(self._model_path):
            logger.info(f"Qwen GGUF 模型未找到: {self._model_path}")
            return
        try:
            from llama_cpp import Llama
            self._model = Llama(
                model_path=self._model_path,
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                verbose=False,
            )
            self._available = True
            logger.info("Qwen Local Provider 就绪 (CPU)")
        except ImportError:
            logger.info("llama-cpp-python 未安装，Qwen Local 不可用")
        except Exception as e:
            logger.warning(f"Qwen 本地模型加载失败: {e}")

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        if not self._model:
            raise RuntimeError("Qwen 本地模型未加载")
        full_prompt = f"{system_prompt}\n\n用户: {user_prompt}\n助手:"
        output = self._model(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["用户:", "\n\n\n"],
            echo=False,
        )
        return output["choices"][0]["text"].strip()

    def health_check(self) -> bool:
        if not self._model:
            return False
        try:
            self._model("你好", max_tokens=10)
            return True
        except Exception:
            self._available = False
            return False

    def is_available(self) -> bool:
        return self._available


class RuleEngineProvider(BaseLLMProvider):
    """L3: 规则引擎 — 纯离线无LLM"""

    provider_name = "rule-engine"

    def __init__(self):
        self._rules = self._load_rules()
        self._available = True
        logger.info("规则引擎 Provider 就绪 (纯离线)")

    def _load_rules(self) -> dict[str, dict]:
        return {
            "过热": {
                "root_cause": "散热系统故障（散热风扇/散热器/风道堵塞）",
                "actions": [
                    "1. 检查散热风扇是否正常运行",
                    "2. 清洁散热器表面灰尘",
                    "3. 检查通风管道是否堵塞",
                    "4. 降低设备负载至70%以下",
                ],
                "risk": "HIGH",
                "confidence": 0.6,
            },
            "振动": {
                "root_cause": "机械部件磨损或松动（轴承/齿轮/螺栓）",
                "actions": [
                    "1. 检测振动频谱确认故障频率",
                    "2. 检查轴承温度和润滑状态",
                    "3. 检查地脚螺栓是否松动",
                    "4. 必要时安排停机检修",
                ],
                "risk": "HIGH",
                "confidence": 0.55,
            },
            "通讯中断": {
                "root_cause": "通讯模块故障或线路问题",
                "actions": [
                    "1. 检查通讯线缆连接是否松动",
                    "2. 重启通讯模块",
                    "3. 检查交换机/路由器工作状态",
                    "4. 如持续中断，更换通讯模块",
                ],
                "risk": "HIGH",
                "confidence": 0.65,
            },
            "绝缘": {
                "root_cause": "绝缘老化或受潮导致绝缘阻抗降低",
                "actions": [
                    "1. 测量绝缘电阻值",
                    "2. 检查设备密封性",
                    "3. 检查是否有凝露或进水",
                    "4. 必要时停机干燥处理",
                ],
                "risk": "CRITICAL",
                "confidence": 0.7,
            },
            "油温": {
                "root_cause": "冷却系统异常或内部故障发热",
                "actions": [
                    "1. 检查冷却系统运行状态",
                    "2. 检测油中溶解气体",
                    "3. 检查油位是否正常",
                    "4. 降低负载运行观察趋势",
                ],
                "risk": "HIGH",
                "confidence": 0.6,
            },
        }

    def _match_rule(self, prompt: str) -> dict:
        for keyword, rule in self._rules.items():
            if keyword in prompt:
                return rule
        return {
            "root_cause": "需人工介入分析，规则引擎无法匹配具体故障模式",
            "actions": [
                "1. 查看设备历史告警记录",
                "2. 收集现场运行数据和照片",
                "3. 联系设备厂家技术支持",
                "4. 如需紧急处理，参考设备运维手册",
            ],
            "risk": "MEDIUM",
            "confidence": 0.3,
        }

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        rule = self._match_rule(user_prompt)
        lines = [
            "## 规则引擎诊断结果 ⚠️（离线降级模式，仅供参考）",
            "",
            f"**可能的根因**: {rule['root_cause']}",
            f"**风险等级**: {rule['risk']}",
            f"**置信度**: {rule['confidence']*100:.0f}%",
            "",
            "**推荐处置步骤**:",
        ]
        for action in rule["actions"]:
            lines.append(action)
        lines.extend([
            "",
            "> ⚠️ 当前为规则引擎降级模式，诊断精度有限。",
            "> 建议尽快恢复网络连接或启动本地推理模型以获得更准确的诊断。",
        ])
        return "\n".join(lines)

    def health_check(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True


class HybridProvider:
    """混合部署调度器 — 自动降级+恢复探测"""

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._current: Optional[BaseLLMProvider] = None
        self._lock = threading.Lock()
        self._recovery_interval = 60
        self._recovery_thread: Optional[threading.Thread] = None
        self._init_providers()

    def _init_providers(self):
        self._providers["deepseek"] = DeepSeekProvider()
        self._providers["qwen-local"] = QwenLocalProvider()
        self._providers["rule-engine"] = RuleEngineProvider()

        self._current = self._select_initial()
        logger.info(f"当前 Provider: {self._current.provider_name}")

        if self._current.provider_name != "deepseek":
            self._start_recovery()

    def _select_initial(self) -> BaseLLMProvider:
        for name in ["deepseek", "qwen-local", "rule-engine"]:
            p = self._providers[name]
            if p.is_available():
                return p
        return self._providers["rule-engine"]

    def _start_recovery(self):
        if self._recovery_thread and self._recovery_thread.is_alive():
            return

        def recover_loop():
            while True:
                time.sleep(self._recovery_interval)
                if self._current.provider_name != "deepseek":
                    deepseek = self._providers["deepseek"]
                    if deepseek.health_check():
                        with self._lock:
                            self._current = deepseek
                        logger.info("DeepSeek API 已恢复，切换回在线模式")

                if self._current.provider_name == "rule-engine":
                    qwen = self._providers["qwen-local"]
                    if qwen.is_available():
                        with self._lock:
                            self._current = qwen
                        logger.info("Qwen Local 已就绪，从规则引擎升级")

        self._recovery_thread = threading.Thread(target=recover_loop, daemon=True)
        self._recovery_thread.start()

    @property
    def current_provider(self) -> BaseLLMProvider:
        return self._current

    @property
    def current_mode(self) -> str:
        return self._current.provider_name

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.1, max_tokens: int = 2048) -> str:
        provider = self._current
        try:
            return provider.chat(system_prompt, user_prompt, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Provider [{provider.provider_name}] 调用失败: {e}")
            self._try_downgrade(provider)
            return self.chat(system_prompt, user_prompt, temperature, max_tokens)

    def chat_json(self, system_prompt: str, user_prompt: str,
                  temperature: float = 0.1) -> dict:
        provider = self._current
        try:
            return provider.chat_json(system_prompt, user_prompt, temperature)
        except Exception as e:
            logger.warning(f"Provider [{provider.provider_name}] JSON调用失败: {e}")
            self._try_downgrade(provider)
            return self.chat_json(system_prompt, user_prompt, temperature)

    def _try_downgrade(self, failed_provider: BaseLLMProvider):
        order = ["deepseek", "qwen-local", "rule-engine"]
        try:
            idx = order.index(failed_provider.provider_name)
        except ValueError:
            return

        for i in range(idx + 1, len(order)):
            p = self._providers[order[i]]
            if p.is_available():
                with self._lock:
                    self._current = p
                logger.warning(f"降级: {failed_provider.provider_name} → {p.provider_name}")
                self._start_recovery()
                return

    def mode_status(self) -> dict:
        return {
            "current": self._current.provider_name,
            "available": {n: p.is_available() for n, p in self._providers.items()},
            "deployment": "online" if self._current.provider_name == "deepseek"
            else ("offline-llm" if self._current.provider_name == "qwen-local"
                  else "offline-rules"),
        }


hybrid_llm = HybridProvider()
