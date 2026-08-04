# 驭能 — 部署指南

> 新能源场站非计划停机智能诊断系统
> 版本 3.1 | 2026-08-04

---

## 一、环境要求

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.11+ | 异步特性需要 |
| Docker | 24.0+ | 容器部署 |
| Docker Compose | 2.20+ | 编排管理 |
| 内存 | 2GB+ | 双模型诊断需 4GB |
| 磁盘 | 10GB+ | 知识库 + 日志 |
| DeepSeek API Key | — | 必须，LLM 推理 |

---

## 二、快速启动（开发）

```bash
# 1. 进入项目目录
cd /home/an/项目/驭能

# 2. 创建虚拟环境
python -m venv venv && source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env 填写 DEEPSEEK_API_KEY

# 5. 启动服务
bash start.sh

# 6. 验证
curl http://localhost:8080/health
# {"status":"healthy","version":"3.0.0"}
```

---

## 三、Docker 部署（生产）

### 3.1 开发/测试环境

```bash
docker compose up -d
docker compose logs -f api
```

### 3.2 生产环境

```bash
# 使用生产配置（独立数据卷、资源限制、日志管理）
docker compose -f docker-compose.prod.yml up -d

# 查看状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f --tail=100 api

# 停止
docker compose -f docker-compose.prod.yml down
```

### 3.3 带 MCP 工具服务（可选）

```bash
docker compose -f docker-compose.prod.yml --profile mcp up -d
```

### 3.4 生产配置特性

| 特性 | 说明 |
|------|------|
| 多阶段构建 | 构建层分离，最终镜像仅 200MB |
| 非 root 用户 | `yuneng` 用户运行，无特权 |
| 数据持久化 | 3 个独立 Docker Volume |
| 健康检查 | 30s 间隔，3 次重试 |
| 日志轮转 | 单文件 100MB，保留 3 个 |
| 资源限制 | API: 4G/2CPU, MCP: 512MB |
| 自动重启 | `unless-stopped` 策略 |

---

## 四、环境变量

### 4.1 必填

| 变量 | 说明 | 示例 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-dcd7...` |

### 4.2 模型配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | 对话模型 | `deepseek-chat` |
| `DEEPSEEK_REASONER_MODEL` | 推理模型 | `deepseek-reasoner` |

### 4.3 诊断引擎

| 变量 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `DIAGNOSIS_MODE` | 诊断模式 | `ensemble` `single` `auto` | `ensemble` |
| `OFFLINE_MODE` | 离线策略 | `auto` `force-online` `force-offline` | `auto` |

### 4.4 多模态（可选）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | 通义千问视觉 API Key | — |
| `QWEN_LOCAL_PATH` | 本地 Qwen GGUF 路径 | — |

### 4.5 服务

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_PORT` | API 端口 | `8080` |
| `MCP_PORT` | MCP 服务端口 | `9901` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## 五、诊断模式

| 模式 | LLM | 速度 | 置信度 | 适用场景 |
|------|-----|------|--------|---------|
| `ensemble` | V4 + R1 双模型 | ~10s | 0.75-0.92 | 生产环境，高精度 |
| `single` | V4 单模型 | ~2s | 0.70-0.85 | 开发调试，快速 |
| `auto` | V4 默认，失败降级 R1 | 2-10s | 0.75-0.92 | 推荐 |

---

## 六、混合部署与自动降级

```
DeepSeek API (在线)
    ↓ 5 次连续失败
Qwen GGUF (本地 CPU 推理)
    ↓ 不可用
规则引擎 (纯离线，35 条专业知识)
```

- 探测间隔 60 秒，恢复后自动切回在线
- 规则引擎内置 35 条设备知识 + 6 种故障匹配规则
- 纯离线模式无需任何网络连接

---

## 七、API 端点

### 7.1 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/dashboard` | 项目进度面板 |
| `GET` | `/api/audit` | 质量审计报告 |
| `GET` | `/api/skills` | Skill/Agent 列表 |
| `GET` | `/api/tools/list` | MCP 工具列表 |

### 7.2 诊断

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/diagnose` | 故障诊断（同步） |
| `POST` | `/api/diagnose/stream` | 故障诊断（SSE 流式） |
| `POST` | `/api/diagnose/multimodal` | 多模态诊断 |
| `POST` | `/api/diagnose/multimodal/stream` | 多模态诊断（流式） |
| `GET` | `/api/diagnose/history` | 诊断历史 |
| `GET` | `/api/diagnose/report/{task_id}` | 诊断报告详情 |

### 7.3 告警

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/alarm/receive` | 接收告警 |
| `POST` | `/api/alarm/diagnose` | 告警诊断 |
| `GET` | `/api/alarm/diagnose/{task_id}/status` | 诊断状态 |
| `GET` | `/api/alarm/checkpoint/{task_id}` | 诊断检查点 |

### 7.4 对话与反馈

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | 对话（同步） |
| `POST` | `/api/chat/stream` | 对话（SSE 流式） |
| `POST` | `/api/chat/clear` | 清除会话 |
| `POST` | `/api/feedback` | 提交反馈 |
| `GET` | `/api/feedback/stats` | 反馈统计 |

### 7.5 知识与数据

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/knowledge/documents/upload` | 上传文档 |
| `POST` | `/api/knowledge/search/test` | 知识库检索 |
| `GET` | `/api/knowledge/health` | 知识库健康 |
| `GET` | `/api/scada/health` | SCADA 健康 |
| `GET` | `/api/scada/devices` | 已连接设备 |
| `GET` | `/api/scada/buffer/stats` | 缓冲区统计 |
| `GET` | `/api/trace/{task_id}/replay` | 诊断轨迹回放 |

---

## 八、测试

```bash
# 非 LLM 测试（秒级）
python -m pytest tests/test_rag.py tests/test_modules.py tests/test_tools.py tests/test_hooks.py -v

# 集成测试（不含 LLM）
python -m pytest tests/test_api.py -v -k "not (TestChat or TestDiagnosis or TestAlarm)"

# 全量测试（含 LLM，较慢）
python -m pytest tests/ -v

# 覆盖率报告
python -m pytest tests/ --cov=app --cov-report=html
```

---

## 九、数据目录

```
knowledge_db/     知识库 (86 条，48 种设备 × 10 类别) + ChromaDB 向量索引
data/             SCADA 数据 + 微调数据集
data/raw/         原始数据
data/processed/   处理后数据
logs/             运行日志
skills/           自动生成的 Skill Prompt
```

---

## 十、故障排查

### 10.1 健康检查失败

```bash
# 查看容器日志
docker compose logs api --tail=50

# 进入容器检查
docker compose exec api python -c "from app.main import app; print('OK')"

# 检查 API Key
docker compose exec api env | grep DEEPSEEK
```

### 10.2 API 返回 500

```bash
# 查看错误日志
docker compose logs api | grep ERROR

# 常见原因:
# - DEEPSEEK_API_KEY 未配置或过期
# - 模型 API 限流
# - 知识库文件损坏: rm -rf knowledge_db/ 重启
```

### 10.3 内存不足

```bash
# 调整 Docker 资源限制
# 编辑 docker-compose.yml
# deploy.resources.limits.memory: 8G

# 或在 .env 中设置:
DIAGNOSIS_MODE=single  # 单模型节省内存
```

### 10.4 端口冲突

```bash
# 修改端口
API_PORT=9090 docker compose up -d

# 检查端口占用
lsof -i :8080
```

---

## 十一、安全注意事项

- `.env` 文件包含 API Key，已被 `.gitignore` 排除，不要提交到 Git
- Docker 容器以非 root 用户 `yuneng` 运行
- 生产环境建议配置反向代理（Nginx）并启用 HTTPS
- SCADA 连接器仅在受控网络内使用，不要暴露到公网
- 定期审查 `logs/` 目录磁盘使用量
