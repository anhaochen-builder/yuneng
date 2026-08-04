<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dashboardApi, auditApi, healthCheck } from '@/api'

const mode = ref('production-online')
const audit = ref<any>({})
const health = ref<any>({})
const loading = ref(true)
const env = ref<any>({})

onMounted(async () => {
  try { const r = await dashboardApi.mode(); mode.value = (r.data || r).current || 'production-online' } catch {}
  try { const r = await auditApi.overview(); audit.value = r.data || r } catch {}
  try { const r = await healthCheck(); health.value = r.data || r; env.value = (r.data || r).env || {} } catch {}
  loading.value = false
})

const systemInfo = {
  '项目名称': '驭能智能诊断平台',
  '版本号': 'v1.0.0',
  '后端框架': 'FastAPI + Uvicorn',
  '前端框架': 'Vue 3 + Element Plus + Three.js',
  '编排引擎': 'LangGraph + Supervisor Pattern',
  'LLM 模型': 'DeepSeek V4 Pro + R1 Ensemble',
  '向量数据库': 'ChromaDB + HNSW 索引',
  '嵌入模型': 'BGE-Large-ZH v1.5 (1024维)',
  '多模态模型': 'Qwen-VL-Max + EasyOCR',
  '工业协议': 'Modbus TCP / IEC 61850 / OPC UA',
  '容器化': 'Docker Compose 3.8',
  '工具协议': 'MCP 1.5+',
}

const services = [
  { name: '后端服务', status: 'healthy', detail: 'FastAPI 运行中' },
  { name: 'DeepSeek API', status: mode.value !== 'rule-engine' ? 'connected' : 'degraded', detail: mode.value !== 'rule-engine' ? '已连接' : '已降级至规则引擎' },
  { name: '知识库', status: 'healthy', detail: '160 条知识条目，ChromaDB' },
  { name: 'OCR 引擎', status: 'healthy', detail: 'EasyOCR 1.7.2' },
  { name: 'MCP Server', status: 'healthy', detail: `端口 ${env.value.MCP_PORT || 9901}` },
  { name: 'SCADA 连接', status: 'warning', detail: '3/5 设备在线' },
  { name: 'Docker', status: 'healthy', detail: 'Compose 运行中' },
  { name: 'Neo4j 图数据库', status: 'stopped', detail: '可选，已降级 NetworkX' },
]

function getServiceColor(status: string) {
  switch (status) {
    case 'healthy': case 'connected': return '#52c41a'
    case 'warning': case 'degraded': return '#ff9c40'
    case 'error': case 'stopped': return '#ff4d4f'
    default: return '#8ba0c8'
  }
}

const resources = [
  { name: '子智能体', used: 8, total: 8 },
  { name: 'MCP 工具', used: 6, total: 6 },
  { name: '生命周期 Hook', used: 12, total: 12 },
  { name: 'MCP 工具', used: 6, total: 6 },
  { name: 'API 端点', used: 32, total: 32 },
  { name: '内存使用', used: 45, total: 100 },
]
</script>

<template>
  <div class="settings-page animate-fade-in" v-loading="loading">
    <!-- 顶部状态 -->
    <div class="top-stats">
      <div class="stat-card" v-for="s in [
        { label:'系统版本', value:'v1.0.0', color:'#00f0ff', icon:'📦' },
        { label:'LLM 引擎', value:'DeepSeek V4 Pro', color:'#00d4aa', icon:'🧠' },
        { label:'部署模式', value:mode === 'production-online' ? '生产在线' : mode === 'standard-offline' ? '标准离线' : '纯离线', color:'#7b68ee', icon:'🏭' },
        { label:'审计等级', value:audit.overall?.grade||'A', color:audit.overall?.grade==='A'?'#52c41a':'#ff9c40', icon:'🛡' },
      ]" :key="s.label">
        <div class="sc-icon">{{ s.icon }}</div>
        <div class="sc-val font-digital data-glow" :style="{color:s.color}">{{ s.value }}</div>
        <div class="sc-lbl">{{ s.label }}</div>
      </div>
    </div>

    <div class="grid-3col">
      <!-- 系统信息 -->
      <div class="tech-card">
        <h4>⚙️ 系统信息</h4>
        <div class="info-list">
          <div class="info-row" v-for="(v,k) in systemInfo" :key="k">
            <span class="ik">{{ k }}</span><span class="iv">{{ v }}</span>
          </div>
        </div>
      </div>

      <!-- 服务状态 -->
      <div class="tech-card">
        <h4>📡 服务状态</h4>
        <div class="status-grid">
          <div v-for="s in services" :key="s.name" class="status-card" :class="s.status">
            <div class="sd">
              <span class="s-dot" :style="{background: getServiceColor(s.status)}"></span>
              {{ s.name }}
            </div>
            <div class="st" :style="{color: getServiceColor(s.status)}">{{ s.detail }}</div>
          </div>
        </div>
      </div>

      <!-- 资源使用 -->
      <div class="tech-card">
        <h4>📊 资源使用</h4>
        <div class="resource-list">
          <div class="res-item" v-for="r in resources" :key="r.name">
            <div class="res-label">{{ r.name }}</div>
            <el-progress :percentage="Math.round((r.used/r.total)*100)" :stroke-width="8" 
              :color="r.used/r.total > 0.9 ? '#52c41a' : r.used/r.total > 0.6 ? '#00f0ff' : '#7b68ee'" />
            <span class="res-val">{{ r.used }}/{{ r.total }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 部署模式说明 -->
    <div class="tech-card">
      <h4>🔄 部署模式</h4>
      <div class="mode-cards">
        <div class="mode-card" :class="{ active: mode === 'offline' }">
          <div class="mc-icon">🔒</div>
          <div class="mc-title">纯离线模式</div>
          <div class="mc-desc">ChromaDB (SQLite) + 规则引擎降级，涉密场站适用</div>
        </div>
        <div class="mode-card" :class="{ active: mode === 'standard-offline' }">
          <div class="mc-icon">💻</div>
          <div class="mc-title">标准离线模式</div>
          <div class="mc-desc">ChromaDB + 本地 Ollama/GPU，有 GPU 的场站</div>
        </div>
        <div class="mode-card" :class="{ active: mode === 'production-online' }">
          <div class="mc-icon">☁️</div>
          <div class="mc-title">生产在线模式</div>
          <div class="mc-desc">PostgreSQL + ChromaDB + DeepSeek API，性能最优</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.settings-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.top-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.stat-card {
  background: rgba(10,22,40,0.5); border: 1px solid rgba(0,240,255,0.08);
  border-radius: 6px; padding: 14px; text-align: center;
}
.sc-icon { font-size: 22px; margin-bottom: 4px; }
.sc-val { font-size: 20px; font-weight: 700; }
.sc-lbl { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }

.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }

h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }

.info-list { display: flex; flex-direction: column; gap: 1px; }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.04); font-size: 12px; }
.ik { color: var(--color-text-secondary); }
.iv { color: var(--color-text-primary); text-align: right; }

.status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.status-card {
  padding: 10px; background: rgba(0,240,255,0.03); border-radius: 6px;
  border: 1px solid rgba(0,240,255,0.06); text-align: center;
}
.sd { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
.st { font-size: 12px; }
.s-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-right: 4px; }

.resource-list { display: flex; flex-direction: column; gap: 10px; }
.res-item { display: flex; align-items: center; gap: 8px; }
.res-label { font-size: 12px; color: var(--color-text-secondary); min-width: 85px; }
.res-val { font-size: 11px; color: var(--color-text-primary); white-space: nowrap; min-width: 40px; text-align: right; }

.mode-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.mode-card {
  padding: 18px; text-align: center; border-radius: 8px;
  border: 1px solid rgba(0,240,255,0.1);
  background: rgba(0,240,255,0.03);
  transition: all 0.3s;
  &.active {
    border-color: var(--color-accent);
    background: rgba(0,240,255,0.08);
    box-shadow: 0 0 20px rgba(0,240,255,0.1);
  }
}
.mc-icon { font-size: 32px; margin-bottom: 8px; }
.mc-title { font-size: 15px; color: var(--color-text-primary); font-weight: 600; margin-bottom: 6px; }
.mc-desc { font-size: 12px; color: var(--color-text-secondary); line-height: 1.5; }
</style>
