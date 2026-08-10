# ⚡ 驭能-风电运维 Yuneng

> 新能源场站非计划停机智能诊断系统 — 给新能源场站配一个"永不休息的急诊专家"

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3.5-brightgreen)](https://vuejs.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-orange)](https://langchain-ai.github.io/langgraph/)

---

## 简介

驭能是一个面向新能源场站（风电场 + 光伏电站）的 **AI 智能诊断系统**。当风机、光伏逆变器、变压器等核心设备突发故障时，系统在 **3-5 分钟内** 自动完成：

**故障诊断 → 处置方案 → 安规审查 → 决策指导** 全链路闭环。

## 核心特性

- **多智能体协同诊断** — 基于 LangGraph 的 Supervisor + 6 子智能体架构，支持并行调度与重规划
- **DeepSeek V4 Pro 驱动** — CoT 四步推理 + 多模型 Ensemble 投票 + 三层降级（API → 本地 GGUF → 规则引擎）
- **9 项结构化报告** — 告警摘要 / 初步判断 / 分析依据 / 可能原因 / 排查步骤 / 处理建议 / 安全风险 / 派单建议 / 风险自复核
- **五维度质量评估** — Judge Agent 独立评分（证据/逻辑/安规/可操作/一致性），< 70 分自动重规划
- **48 种设备知识图谱** — 覆盖风力/光伏/储能/变电/线路等 10 大类别，100+ 故障模式
- **混合 RAG 检索引擎** — 向量检索 + BM25 + RRF 融合 + BGE CrossEncoder 精排
- **多模态诊断** — Qwen-VL-Max 图像分析（红外热像/电气图/设备外观）+ librosa 音频频谱分析 + Cross-Attention 融合
- **SCADA 数据集成** — Modbus TCP / IEC 61850 / OPC UA 三协议适配 + 180 万条环形缓冲区
- **三层记忆系统** — 短期 / 工作 / 长期记忆 + 指数时间衰减检索
- **主动学习** — 成功案例自动入库 + Skill 自动生成
- **SSE 流式输出** — 7 个节点实时进度推送
- **离线降级** — 断网自动切换本地模型或规则引擎，极限情况仍可诊断

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn (异步 ASGI) |
| **AI 引擎** | DeepSeek V4 Pro / R1 / Qwen-Max + 本地 GGUF |
| **工作流** | LangGraph StateGraph + SqliteSaver 持久化 |
| **向量数据库** | ChromaDB (HNSW 索引) |
| **嵌入模型** | BAAI/bce-embedding-base_v1 (768D) |
| **重排模型** | BAAI/bge-reranker-v2-m3 (CrossEncoder) |
| **多模态** | Qwen-VL-Max (图像) + librosa + numpy FFT (音频) |
| **文档解析** | PyMuPDF / python-docx / openpyxl |
| **前端** | Vue 3 + Element Plus + ECharts + Three.js |
| **部署** | Docker Compose + Nginx |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- DeepSeek API Key ([注册](https://platform.deepseek.com))

### 安装

```bash
# 克隆仓库
git clone https://github.com/anhaochen-builder/yuneng.git
cd yuneng

# 后端
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 前端
cd frontend
npm install
npm run build
cd ..

# 启动
python -m app.main
# 访问 http://localhost:8080
```

### Docker 部署

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
docker compose up -d
```

## 项目结构

```
yuneng/
├── app/                    # 后端核心
│   ├── agent/              # AI Agent（路由/诊断/裁判/审查/多模型）
│   ├── api/                # 18 个 API 路由模块
│   ├── graph/              # LangGraph 编排（状态/路由/子智能体/Hook）
│   ├── rag/                # RAG 引擎（混合检索/重排/知识图谱/GraphRAG/文档解析）
│   ├── scada/              # SCADA 数据层（协议适配/环形缓冲区/标准化）
│   ├── multimodal/         # 多模态（图像/音频/Cross-Attention融合）
│   ├── memory/             # 三层记忆系统
│   ├── learning/           # 主动学习（案例入库/Skill生成）
│   ├── utils/              # 工具（缓存/熔断/认证/日志）
│   └── main.py             # FastAPI 入口
├── frontend/               # Vue 3 前端
├── mcp_server/             # MCP 工具服务
├── scripts/                # 数据导入/评估/LoRA微调脚本
├── tests/                  # 327 测试用例
├── skills/                 # 诊断 Skill 定义
├── docker-compose.yml      # Docker 部署配置
└── requirements.txt        # Python 依赖
```

## API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| chat | `POST /api/chat` | 对话（SSE 流式） |
| diagnosis | `POST /api/diagnosis` | 故障诊断 |
| alarm | `POST /api/alarm` | 告警诊断 |
| knowledge | `POST /api/knowledge` | 知识库管理 |
| scada | `POST /api/scada` | SCADA 数据查询 |
| feedback | `POST /api/feedback` | RLHF 反馈 |
| trace | `GET /api/trace/{id}/replay` | 诊断回放 |
| dashboard | `GET /api/dashboard` | 进度监控 |

## 测试

```bash
# 运行全部测试（327 用例）
pytest tests/ -q

# 性能压测
pytest tests/test_performance.py -q

# MCP 工具测试
pytest tests/test_mcp.py -q
```

## 文档

- [全链路技术分析文档](./驭能-全链路技术分析文档.md)
- [部署指南](./DEPLOY.md)

## 许可证

MIT License © 2026 安嘉俊

---

> ⚠️ 本系统诊断为 AI 辅助分析，仅供参考。涉及设备停运、并网解列的操作决策，必须经值长或专工人工确认后执行。
