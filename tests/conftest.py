"""测试配置和共享fixtures"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DISABLE_AUTH"] = "1"

import pytest
from app.graph.sub_agent_init import register_all


@pytest.fixture(scope="session", autouse=True)
def setup_subagents():
    register_all()


@pytest.fixture(scope="session")
def auth_token():
    from app.utils.auth import create_token
    return create_token("admin", "admin")


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def unwrap(response):
    """解包统一响应格式 {code, data, message} → 返回 data 部分"""
    import json
    body = response.json()
    if isinstance(body, dict) and "data" in body and "code" in body:
        return body["data"]
    return body


@pytest.fixture
def sample_symptoms():
    return "逆变器IGBT模块过温报警，设备INV005，NTC温度98°C超过保护阈值"


@pytest.fixture
def sample_device_id():
    return "INV005"
