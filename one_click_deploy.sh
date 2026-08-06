#!/bin/bash
# 驭能智能诊断平台 — 一键部署脚本
# 用法: bash one_click_deploy.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${CYAN}[驭能]${NC} $1"; }
ok()  { echo -e "${GREEN}  ✅ $1${NC}"; }
err(){ echo -e "${RED}  ❌ $1${NC}"; }

echo "========================================"
echo "  驭能智能诊断平台 — 一键部署 v1.5.0"
echo "========================================"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1. 环境检查
log "检查 Python 环境..."
python3 --version > /dev/null 2>&1 || { err "需要 Python 3.11+"; exit 1; }
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Python $PYVER"

log "检查依赖..."
if [ ! -d "venv" ]; then
    log "创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q 2>/dev/null
pip install langgraph-checkpoint-sqlite aiosqlite -q 2>/dev/null
ok "依赖已安装"

# 2. 配置初始化
log "初始化配置..."
[ ! -f .env ] && cp .env.example .env 2>/dev/null || true
grep -q "DEEPSEEK_API_KEY" .env 2>/dev/null || echo "DEEPSEEK_API_KEY=your_api_key_here" >> .env
ok ".env 已就绪"

python3 -c "
from app.utils.auth import _save_users, USER_STORE
if 'admin' not in USER_STORE:
    USER_STORE['admin'] = {'username':'admin','password':'8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918','role':'admin'}
    _save_users()
    print('管理员账号已初始化: admin / admin123')
"
ok "管理员账号: admin / admin123"

# 3. 知识库初始化
log "初始化知识库..."
python3 -c "
from pathlib import Path
kb_dir = Path('knowledge_db')
kb_dir.mkdir(parents=True, exist_ok=True)
kb_file = kb_dir / 'knowledge.json'
if not kb_file.exists():
    print('知识库为空，将使用内置数据')
else:
    print('知识库已就绪')
"
ok "知识库已就绪"

# 4. 启动服务
log "启动服务..."
PORT=${API_PORT:-8080}
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT > logs/server.log 2>&1 &
PID=$!
echo $PID > .pid

sleep 5
if kill -0 $PID 2>/dev/null; then
    ok "服务已启动 (PID: $PID)"
else
    err "服务启动失败，查看 logs/server.log"
    exit 1
fi

# 5. 等待就绪
log "等待服务就绪..."
for i in $(seq 1 30); do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        ok "服务就绪"
        break
    fi
    sleep 3
done

# 6. 验证
echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"
echo "  访问地址: http://localhost:$PORT"
echo "  管理账号: admin / admin123"
echo "  API 文档: http://localhost:$PORT/docs"
echo ""
echo "  Webhook 告警接入: POST http://localhost:$PORT/api/external/webhook/alarm"
echo "  设备发现: GET http://localhost:$PORT/api/automation/discovery?scan_network=true"
echo "  每日自动巡检: POST http://localhost:$PORT/api/automation/notify/run-now"
echo ""
echo "  停止服务: kill \$(cat .pid)"
echo "  查看日志: tail -f logs/server.log"
echo "========================================"
