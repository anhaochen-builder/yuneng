"""运行时配置 API — 支持热切换 LLM / API Key"""
import json
import logging
import os
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "runtime_config.json"

PRESET_MODELS = [
    {"label": "DeepSeek V4 (推荐)", "provider": "deepseek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "reasoner": "deepseek-reasoner"},
    {"label": "DeepSeek R1 (精准)", "provider": "deepseek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-reasoner", "reasoner": "deepseek-reasoner"},
    {"label": "OpenAI GPT-4o", "provider": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-4o", "reasoner": "gpt-4o"},
    {"label": "通义千问 Qwen-Max", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-max", "reasoner": "qwen-max"},
    {"label": "通义千问 Qwen-Plus", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "reasoner": "qwen-plus"},
    {"label": "Moonshot Kimi", "provider": "moonshot", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k", "reasoner": "moonshot-v1-8k"},
    {"label": "智谱 GLM-4", "provider": "zhipu", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4", "reasoner": "glm-4"},
    {"label": "自定义", "provider": "custom", "base_url": "", "model": "", "reasoner": ""},
]


class LLMConfig(BaseModel):
    api_key: str = Field(default="", description="API Key")
    base_url: str = Field(default="", description="API 地址")
    model: str = Field(default="", description="对话模型")
    reasoner_model: str = Field(default="", description="推理模型")


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _save_config(data: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if data.get("llm"):
        _apply_llm_config(data["llm"])


def _apply_llm_config(cfg: dict):
    api_key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "")
    model = cfg.get("model", "")

    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
    if base_url:
        os.environ["DEEPSEEK_BASE_URL"] = base_url
    if model:
        os.environ["DEEPSEEK_MODEL"] = model
    if cfg.get("reasoner_model"):
        os.environ["DEEPSEEK_REASONER_MODEL"] = cfg["reasoner_model"]

    try:
        from app.agent.llm_client import _llm_instance
        import app.agent.llm_client as llm_mod
        llm_mod._llm_instance = None
        from app.agent.multi_model import multi_client
        multi_client._clients.clear()
        multi_client.__init__()
        logger.info("LLM 客户端已重新初始化")
    except Exception as e:
        logger.warning(f"LLM 热重载失败（需重启服务）: {e}")


@router.get("/llm")
async def get_llm_config():
    data = _load_config()
    llm = data.get("llm", {})
    return {
        "api_key": llm.get("api_key", ""),
        "base_url": llm.get("base_url", os.getenv("DEEPSEEK_BASE_URL", "")),
        "model": llm.get("model", os.getenv("DEEPSEEK_MODEL", "")),
        "reasoner_model": llm.get("reasoner_model", os.getenv("DEEPSEEK_REASONER_MODEL", "")),
        "presets": PRESET_MODELS,
    }


@router.post("/llm")
async def update_llm_config(req: LLMConfig):
    data = _load_config()
    existing = data.get("llm", {})

    if req.api_key:
        existing["api_key"] = req.api_key
    if req.base_url:
        existing["base_url"] = req.base_url
    if req.model:
        existing["model"] = req.model
    if req.reasoner_model:
        existing["reasoner_model"] = req.reasoner_model

    data["llm"] = existing
    _save_config(data)
    return {"status": "saved", "config": existing}


@router.post("/llm/reset")
async def reset_llm_config():
    data = _load_config()
    data.pop("llm", None)
    _save_config(data)
    return {"status": "reset"}
