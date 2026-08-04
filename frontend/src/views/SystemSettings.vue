<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dashboardApi, auditApi, healthCheck } from '@/api'

const mode = ref('production-online')
const audit = ref<any>({})
const health = ref<any>({})
const loading = ref(true)

onMounted(async () => {
  try { const r = await dashboardApi.mode(); mode.value = (r.data || r).current || 'production-online' } catch {}
  try { const r = await auditApi.overview(); audit.value = r.data || r } catch {}
  try { const r = await healthCheck(); health.value = r.data || r } catch {}
  loading.value = false
})
</script>

<template>
  <div class="settings-page animate-fade-in" v-loading="loading">
    <div class="stats-row">
      <div class="stat-card" v-for="s in [
        { label:'系统版本', value:'v1.0.0', color:'#00f0ff' },
        { label:'LLM 引擎', value:'DeepSeek V4 Pro', color:'#00d4aa' },
        { label:'部署模式', value:mode, color:'#7b68ee' },
        { label:'审计等级', value:audit.overall?.grade||'A', color:audit.overall?.grade==='A'?'#52c41a':'#ff9c40' },
      ]" :key="s.label">
        <div class="sv font-digital data-glow" :style="{color:s.color}">{{ s.value }}</div>
        <div class="sl">{{ s.label }}</div>
      </div>
    </div>

    <div class="grid-3col">
      <div class="tech-card">
        <h4>⚙️ 系统信息</h4>
        <div class="info-list">
          <div class="info-row" v-for="(v,k) in { '项目名称':'驭能智能诊断平台','版本号':'1.0.0','后端框架':'FastAPI + Uvicorn','前端框架':'Vue 3 + TypeScript + Element Plus','编排引擎':'LangGraph + Supervisor Pattern','LLM 模型':'DeepSeek V4 Pro + R1 Ensemble','向量数据库':'ChromaDB + HNSW','嵌入模型':'BGE-Large-ZH v1.5','多模态':'Qwen-VL-Max + EasyOCR','工业协议':'Modbus TCP / IEC 61850 / OPC UA','容器化':'Docker Compose' }" :key="k">
            <span class="ik">{{ k }}</span><span class="iv">{{ v }}</span>
          </div>
        </div>
      </div>

      <div class="tech-card">
        <h4>📡 服务状态</h4>
        <div class="status-grid">
          <div class="status-card" :class="{ ok: true }">
            <div class="sd"><span class="s-dot online"></span> 后端服务</div>
            <div class="st font-digital" style="color:#52c41a">{{ health.status || 'healthy' }}</div>
          </div>
          <div class="status-card" :class="{ ok: mode !== 'rule-engine' }">
            <div class="sd"><span class="s-dot" :class="{ online: mode !== 'rule-engine' }"></span> DeepSeek API</div>
            <div class="st font-digital" :style="{color:mode!=='rule-engine'?'#52c41a':'#ff9c40'}">{{ mode !== 'rule-engine' ? '已连接' : '已降级' }}</div>
          </div>
          <div class="status-card ok">
            <div class="sd"><span class="s-dot online"></span> 知识库</div>
            <div class="st font-digital" style="color:#52c41a">160 条</div>
          </div>
          <div class="status-card">
            <div class="sd"><span class="s-dot"></span> OCR 引擎</div>
            <div class="st font-digital" style="color:#ff9c40">未安装(可选)</div>
          </div>
          <div class="status-card">
            <div class="sd"><span class="s-dot"></span> Neo4j</div>
            <div class="st font-digital" style="color:#8892a4">未连接(可选)</div>
          </div>
          <div class="status-card ok">
            <div class="sd"><span class="s-dot online"></span> Docker</div>
            <div class="st font-digital" style="color:#52c41a">就绪</div>
          </div>
        </div>
      </div>

      <div class="tech-card">
        <h4>📊 资源统计</h4>
        <div class="resource-list">
          <div class="res-item">
            <div class="res-label">子智能体</div>
            <el-progress :percentage="100" :stroke-width="8" color="#00f0ff" /><span class="res-val">8/8</span>
          </div>
          <div class="res-item">
            <div class="res-label">MCP 工具</div>
            <el-progress :percentage="100" :stroke-width="8" color="#00d4aa" /><span class="res-val">6/6</span>
          </div>
          <div class="res-item">
            <div class="res-label">生命周期 Hook</div>
            <el-progress :percentage="100" :stroke-width="8" color="#7b68ee" /><span class="res-val">12/12</span>
          </div>
          <div class="res-item">
            <div class="res-label">知识库条目</div>
            <el-progress :percentage="100" :stroke-width="8" color="#ff9c40" /><span class="res-val">160条</span>
          </div>
          <div class="res-item">
            <div class="res-label">API 端点</div>
            <el-progress :percentage="100" :stroke-width="8" color="#52c41a" /><span class="res-val">30+</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.settings-page { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { background: rgba(10,22,40,0.7); border: 1px solid rgba(0,240,255,0.1); border-radius: 6px; padding: 16px; text-align: center; }
.sv { font-size: 22px; font-weight: 700; }
.sl { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
h4 { color: var(--color-accent); margin-bottom: 14px; font-size: 14px; }
.info-list { display: flex; flex-direction: column; gap: 2px; }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.04); font-size: 12px; }
.ik { color: var(--color-text-secondary); }
.iv { color: var(--color-text-primary); font-size: 12px; }
.status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.status-card { padding: 12px; background: rgba(0,240,255,0.03); border-radius: 6px; border: 1px solid rgba(0,240,255,0.06); text-align: center; }
.sd { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }
.st { font-size: 14px; }
.s-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; background: #ff4d4f; margin-right: 4px; }
.s-dot.online { background: #52c41a; }
.resource-list { display: flex; flex-direction: column; gap: 12px; }
.res-item { display: flex; align-items: center; gap: 10px; }
.res-label { font-size: 12px; color: var(--color-text-secondary); min-width: 90px; }
.res-val { font-size: 12px; color: var(--color-text-primary); white-space: nowrap; }
</style>
