# 驭能 — 部署指南

## 快速启动

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env 填写 DEEPSEEK_API_KEY

# 2. 启动
bash start.sh

# 3. 验证
curl http://localhost:8080/health
```

## Docker 部署

```bash
docker compose up -d
docker compose logs -f api
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DEEPSEEK_API_KEY | DeepSeek API Key | — |
| DEEPSEEK_MODEL | 模型名称 | deepseek-chat |
| DEEPSEEK_REASONER_MODEL | R1推理模型 | deepseek-reasoner |
| DASHSCOPE_API_KEY | Qwen DashScope Key(可选) | — |
| DIAGNOSIS_MODE | 诊断模式 ensemble/single/auto | ensemble |
| OFFLINE_MODE | 离线模式 auto/force-offline | auto |
| QWEN_LOCAL_PATH | 本地Qwen GGUF路径(可选) | — |
| API_PORT | 服务端口 | 8080 |
| LOG_LEVEL | 日志级别 | INFO |

## 诊断模式说明

| 模式 | LLM调用 | 速度 | 置信度 | 适用 |
|------|---------|------|--------|------|
| ensemble | V4+R1双模型 | ~10s | 0.75-0.92 | 生产环境 |
| single | V4单模型 | ~2s | 0.70-0.85 | 开发调试 |
| auto | V4为主,R1降级 | 2-10s | 0.75-0.92 | 推荐 |

## 混合部署架构

```
DeepSeek API (在线) → 不可用 → Qwen GGUF (本地CPU)
                                    ↓ 不可用
                               规则引擎 (纯离线)
```

系统自动降级，60秒探测恢复。规则引擎内置35条专业知识+6种故障匹配规则。

## 端口

| 端口 | 说明 |
|------|------|
| 8080 | API 服务 |
| /health | 健康检查 |
| /api/dashboard | 项目进度 |
| /api/audit | 质量审计 |
| /api/diagnose | 故障诊断 |

## 测试

```bash
# 非LLM测试(秒级)
python -m pytest tests/test_rag.py tests/test_modules.py -v

# 全部测试(含LLM, 较慢)
python -m pytest tests/ -v
```

## 数据目录

```
knowledge_db/    — 知识库(35条) + 图数据
data/            — SCADA数据 + 微调数据集
logs/            — 运行日志
skills/          — 自动生成的Skill
```
