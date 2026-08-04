# 驭能 — 多阶段 Docker 构建
# 阶段一: 依赖安装 (利用 Docker 层缓存加速)
# 阶段二: 生产运行 (精简镜像)

# ========== Stage 1: builder ==========
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ========== Stage 2: runtime ==========
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY mcp_server/ ./mcp_server/
COPY skills/ ./skills/
COPY data/ ./data/
COPY knowledge_db/ ./knowledge_db/
COPY scripts/ ./scripts/

RUN mkdir -p /app/data /app/knowledge_db /app/logs

RUN useradd --create-home --shell /bin/bash yuneng && chown -R yuneng:yuneng /app
USER yuneng

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
