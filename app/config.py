"""驭能 - 全局配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_reasoner_model: str = os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner")

    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-max"

    diagnosis_mode: str = os.getenv("DIAGNOSIS_MODE", "ensemble")

    qwen_local_path: str = os.getenv("QWEN_LOCAL_PATH", "")
    offline_mode: str = os.getenv("OFFLINE_MODE", "auto")

    # 向量数据库
    vector_db_path: str = os.getenv("VECTOR_DB_PATH", str(BASE_DIR / "knowledge_db"))
    knowledge_path: str = os.getenv("KNOWLEDGE_PATH", str(BASE_DIR / "data"))

    # 服务
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8080"))
    mcp_port: int = int(os.getenv("MCP_PORT", "9901"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # 数据
    data_dir: str = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    raw_data_dir: str = os.getenv("RAW_DATA_DIR", str(BASE_DIR / "data" / "raw"))
    processed_data_dir: str = os.getenv("PROCESSED_DATA_DIR", str(BASE_DIR / "data" / "processed"))

    # 诊断引擎
    max_retries: int = 2
    confidence_threshold: float = 0.7
    diagnosis_temperature: float = 0.1
    max_tokens: int = 8192


settings = Settings()
