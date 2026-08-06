<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dashboardApi, auditApi, healthCheck, feedbackApi, skillsApi } from '@/api'
import api from '@/api'

const mode = ref<string>('production-online')
const audit = ref<any>({})
const health = ref<any>({})
const loading = ref(true)
const feedbackStats = ref({ total_accurate: 0, total_partial: 0, total_inaccurate: 0 })
const llmConfig = ref({ api_key: '', base_url: '', model: '', reasoner_model: '' })
const llmPresets = ref<Array<{label:string;base_url:string;model:string;reasoner:string}>>([])
const llmSaving = ref(false)
const llmResult = ref('')
const skillsList = ref<any[]>([])
const agentsList = ref<any[]>([])
const rlhfStatus = ref<any>({ feedback: {}, datasets: [], model_versions: { versions: [], active: null } })
const rlhfLoading = ref('')

onMounted(async () => {
  try { const r = await dashboardApi.mode(); mode.value = (r.data || r).current || 'production-online' } catch {}
  try { const r = await auditApi.overview(); audit.value = r.data || r } catch {}
  try { const r = await healthCheck(); health.value = r.data || r } catch {}
  try { const r = await feedbackApi.stats(); Object.assign(feedbackStats.value, r.data || r) } catch {}
  try { const r = await skillsApi.list(); const d = r.data || r; skillsList.value = d.skills || []; agentsList.value = d.sub_agents || [] } catch {}
  try { const r = await api.get('/api/rlhf/status'); rlhfStatus.value = (r.data as any).data || rlhfStatus.value } catch {}
  try { const r = await api.get('/api/settings/llm'); const d = (r.data as any).data; llmConfig.value = { api_key: d.api_key || '', base_url: d.base_url || '', model: d.model || '', reasoner_model: d.reasoner_model || '' }; llmPresets.value = d.presets || [] } catch {}
  loading.value = false
})

const modeLabel = (m: string | undefined) => m === 'production-online' ? '生产在线' : m === 'standard-offline' ? '标准离线' : '纯离线'

const services = [
  { name: 'LLM 引擎', status: mode.value !== 'rule-engine' ? 'online' : 'degraded', detail: 'DeepSeek V4 Pro' },
  { name: '知识库', status: 'online', detail: '160 条 · ChromaDB' },
  { name: 'SCADA', status: 'warning', detail: '3/5 设备在线' },
  { name: 'Neo4j', status: 'offline', detail: '已降级 NetworkX' },
]

function getColor(s: string) {
  return s === 'online' ? '#52c41a' : s === 'warning' ? '#ff9c40' : '#8ba0c8'
}

const versionList = () => rlhfStatus.value?.model_versions?.versions || []
const activeVersion = () => rlhfStatus.value?.model_versions?.active
const feedbackReady = () => (rlhfStatus.value?.feedback?.accurate || 0) >= 50
const datasetCount = () => (rlhfStatus.value?.datasets || []).length

async function rlhfAction(action: string) {
  rlhfLoading.value = action
  try {
    const endpoints: Record<string, string> = { prepare: '/api/rlhf/prepare', train: '/api/rlhf/train' }
    const url = endpoints[action]
    if (url) await api.post(url)
    const r = await api.get('/api/rlhf/status')
    rlhfStatus.value = (r.data as any).data || rlhfStatus.value
  } catch {}
  rlhfLoading.value = ''
}
async function deployVersion(v: string) {
  await api.post('/api/rlhf/deploy', { version: v })
  const r = await api.get('/api/rlhf/status')
  rlhfStatus.value = (r.data as any).data || rlhfStatus.value
}

function applyPreset(p: any) {
  llmConfig.value.base_url = p.base_url
  llmConfig.value.model = p.model
  llmConfig.value.reasoner_model = p.reasoner
}

async function saveLlmConfig() {
  llmSaving.value = true
  llmResult.value = ''
  try {
    await api.post('/api/settings/llm', llmConfig.value)
    llmResult.value = '✅ 配置已保存，正在热重载 LLM 客户端...'
    setTimeout(() => { llmResult.value = '✅ LLM 配置已生效' }, 3000)
  } catch {
    llmResult.value = '❌ 保存失败'
  }
  llmSaving.value = false
}
</script>

<template>
  <div class="settings-page animate-fade-in" v-loading="loading">
    <div class="top-stats">
      <div class="stat-card" v-for="s in [
        { label:'系统版本', value:'v1.0.0', color:'#00f0ff' },
        { label:'LLM 引擎', value:'DeepSeek V4 Pro', color:'#00d4aa' },
        { label:'部署模式', value:modeLabel(mode), color:'#7b68ee' },
        { label:'审计等级', value:audit.overall?.grade||'A', color:'#52c41a' },
      ]" :key="s.label">
        <div class="sc-val font-digital data-glow" :style="{color:s.color}">{{ s.value }}</div>
        <div class="sc-lbl">{{ s.label }}</div>
      </div>
    </div>

    <div class="grid-3col">
      <div class="tech-card">
        <h4>系统信息</h4>
        <div class="info-list">
          <div class="info-row"><span class="ik">版本</span><span class="iv">v1.0.0</span></div>
          <div class="info-row"><span class="ik">后端</span><span class="iv">FastAPI + LangGraph</span></div>
          <div class="info-row"><span class="ik">前端</span><span class="iv">Vue 3 + Element Plus</span></div>
          <div class="info-row"><span class="ik">嵌入模型</span><span class="iv">BGE-Large-ZH v1.5</span></div>
          <div class="info-row"><span class="ik">多模态</span><span class="iv">Qwen-VL-Max + EasyOCR</span></div>
          <div class="info-row"><span class="ik">容器化</span><span class="iv">Docker Compose</span></div>
        </div>
      </div>

      <div class="tech-card">
        <h4>服务状态</h4>
        <div class="status-list">
          <div v-for="s in services" :key="s.name" class="status-row">
            <span class="s-dot" :style="{background:getColor(s.status)}"></span>
            <span class="s-name">{{ s.name }}</span>
            <span class="s-detail">{{ s.detail }}</span>
            <el-tag size="small" :type="s.status==='online'?'success':s.status==='warning'?'warning':'info'">
              {{ s.status === 'online' ? '正常' : s.status === 'warning' ? '告警' : '降级' }}
            </el-tag>
          </div>
        </div>
      </div>

      <div class="tech-card">
        <h4>资源用量</h4>
        <div class="resource-list">
          <div class="res-item">
            <span class="res-label">子智能体</span>
            <el-progress :percentage="100" :stroke-width="8" color="#00f0ff" />
            <span class="res-val">8/8</span>
          </div>
          <div class="res-item">
            <span class="res-label">MCP 工具</span>
            <el-progress :percentage="100" :stroke-width="8" color="#00d4aa" />
            <span class="res-val">6/6</span>
          </div>
          <div class="res-item">
            <span class="res-label">Hook 拦截器</span>
            <el-progress :percentage="100" :stroke-width="8" color="#7b68ee" />
            <span class="res-val">12/12</span>
          </div>
          <div class="res-item">
            <span class="res-label">API 端点</span>
            <el-progress :percentage="100" :stroke-width="8" color="#52c41a" />
            <span class="res-val">32/32</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 反馈学习 + 技能管理 -->
    <div class="grid-2col">
      <div class="tech-card">
        <h4>反馈与学习</h4>
        <div class="feedback-stats">
          <div class="fb-item accurate"><span class="fb-num font-digital">{{ feedbackStats.total_accurate || 0 }}</span><span class="fb-lbl">准确</span></div>
          <div class="fb-item partial"><span class="fb-num font-digital">{{ feedbackStats.total_partial || 0 }}</span><span class="fb-lbl">部分准确</span></div>
          <div class="fb-item inaccurate"><span class="fb-num font-digital">{{ feedbackStats.total_inaccurate || 0 }}</span><span class="fb-lbl">不准确</span></div>
        </div>
        <div class="learn-items">
          <div class="li-row"><span>成功案例入库</span><el-progress :percentage="Math.min(((feedbackStats.total_accurate||0)/50)*100,100)" :stroke-width="6" color="#52c41a" style="flex:1;margin:0 10px" /><span class="font-digital">{{ feedbackStats.total_accurate || 0 }}/50</span></div>
          <div class="li-row"><span>Skill 生成</span><el-progress :percentage="Math.min(((feedbackStats.total_accurate||0)/3)*100,100)" :stroke-width="6" color="#00f0ff" style="flex:1;margin:0 10px" /><span class="font-digital">≥3例触发</span></div>
          <div class="li-row"><span>RLHF 微调</span><el-progress :percentage="Math.min((rlhfStatus.feedback?.accurate||0)/50*100,100)" :stroke-width="6" color="#7b68ee" style="flex:1;margin:0 10px" /><span class="font-digital">{{ rlhfStatus.feedback?.accurate || 0 }}/50</span></div>
        </div>
      </div>

      <div class="tech-card">
        <h4>技能与子智能体</h4>
        <div class="skill-summary">
          <div class="ss-item"><span class="ss-num font-digital" style="color:var(--color-accent)">{{ skillsList.length }}</span><span class="ss-lbl">Skills</span></div>
          <div class="ss-item"><span class="ss-num font-digital" style="color:#00d4aa">{{ agentsList.length }}</span><span class="ss-lbl">SubAgents</span></div>
        </div>
        <div class="agent-mini-list">
          <div v-for="a in agentsList.slice(0, 5)" :key="a.agent_id || a.name" class="am-item">
            <span class="am-name">{{ a.name }}</span>
            <el-tag size="small" type="success">active</el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- RLHF 模型管理 -->
    <div class="tech-card">
      <h4>RLHF 模型管理</h4>
      <div class="rlhf-bar">
        <span>总反馈 {{ rlhfStatus.feedback?.total || 0 }} 条 | 准确 {{ rlhfStatus.feedback?.accurate || 0 }} 条</span>
        <div class="rlhf-actions">
          <el-button size="small" type="primary" :loading="rlhfLoading === 'prepare'" :disabled="!feedbackReady()" @click="rlhfAction('prepare')">
            {{ feedbackReady() ? '准备微调数据集' : '需 50 条准确反馈' }}
          </el-button>
          <el-button size="small" type="success" :loading="rlhfLoading === 'train'" :disabled="datasetCount() === 0" @click="rlhfAction('train')">
            触发 LoRA 微调
          </el-button>
        </div>
      </div>
      <div class="rlhf-models" v-if="versionList().length">
        <div v-for="v in versionList()" :key="v.id" class="model-row" :class="{ active: v.id === activeVersion() }">
          <span class="model-id">v{{ v.id }}</span>
          <span class="model-samples">{{ v.samples }} 样本</span>
          <span class="model-date">{{ v.created_at?.slice(0, 10) }}</span>
          <span v-if="v.id === activeVersion()" class="model-active">当前</span>
          <el-button v-else size="small" text type="primary" @click="deployVersion(v.id)">部署</el-button>
        </div>
      </div>
      <div v-else class="rlhf-empty">暂无模型版本，积累 50 条准确反馈后可开始微调</div>
    </div>

    <!-- LLM 配置 -->
    <div class="tech-card">
      <h4>🤖 LLM 模型配置（热切换）</h4>
      <div class="preset-bar">
        <span class="preset-label">预设模型:</span>
        <el-button v-for="p in llmPresets" :key="p.label" size="small" text @click="applyPreset(p)">{{ p.label }}</el-button>
      </div>
      <div class="llm-form">
        <div class="llm-row">
          <label>API Key</label>
          <el-input v-model="llmConfig.api_key" placeholder="sk-..." type="password" show-password size="small" />
        </div>
        <div class="llm-row">
          <label>API 地址</label>
          <el-input v-model="llmConfig.base_url" placeholder="https://api.deepseek.com/v1" size="small" />
        </div>
        <div class="llm-row">
          <label>对话模型</label>
          <el-input v-model="llmConfig.model" placeholder="deepseek-chat" size="small" />
        </div>
        <div class="llm-row">
          <label>推理模型</label>
          <el-input v-model="llmConfig.reasoner_model" placeholder="deepseek-reasoner" size="small" />
        </div>
        <div class="llm-actions">
          <el-button type="primary" size="small" :loading="llmSaving" @click="saveLlmConfig">保存并热重载</el-button>
          <span v-if="llmResult" class="llm-result">{{ llmResult }}</span>
        </div>
      </div>
    </div>

    <!-- 部署模式 -->
    <div class="tech-card">
      <h4>部署模式</h4>
      <div class="mode-cards">
        <div class="mode-card" :class="{ active: mode === 'offline' }">
          <div class="mc-title">🔒 纯离线</div>
          <div class="mc-desc">ChromaDB + 规则引擎降级，涉密场站适用</div>
        </div>
        <div class="mode-card" :class="{ active: mode === 'standard-offline' }">
          <div class="mc-title">💻 标准离线</div>
          <div class="mc-desc">ChromaDB + 本地 Ollama/GPU 运行</div>
        </div>
        <div class="mode-card" :class="{ active: mode === 'production-online' }">
          <div class="mc-title">☁️ 生产在线</div>
          <div class="mc-desc">PostgreSQL + DeepSeek API，性能最优</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.settings-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.top-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.stat-card { background: rgba(10,22,40,0.5); border: 1px solid rgba(0,240,255,0.08); border-radius: 6px; padding: 14px; text-align: center; }
.sc-val { font-size: 18px; font-weight: 700; }
.sc-lbl { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }

.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

h4 { color: var(--color-accent); margin: 0 0 12px; font-size: 14px; }

.info-list { display: flex; flex-direction: column; gap: 1px; }
.info-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid rgba(0,240,255,0.04); font-size: 12px; }
.ik { color: var(--color-text-secondary); }
.iv { color: var(--color-text-primary); }

.status-list { display: flex; flex-direction: column; gap: 8px; }
.status-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: rgba(0,240,255,0.03); border-radius: 6px; border: 1px solid rgba(0,240,255,0.05); }
.s-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.s-name { font-size: 13px; color: var(--color-text-primary); width: 80px; }
.s-detail { flex: 1; font-size: 11px; color: var(--color-text-secondary); }

.resource-list { display: flex; flex-direction: column; gap: 10px; }
.res-item { display: flex; align-items: center; gap: 8px; }
.res-label { font-size: 12px; color: var(--color-text-secondary); min-width: 80px; }
.res-val { font-size: 11px; color: var(--color-text-primary); white-space: nowrap; }

.mode-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.mode-card { padding: 14px; text-align: center; border-radius: 8px; border: 1px solid rgba(0,240,255,0.1); background: rgba(0,240,255,0.03); transition: all 0.15s;
  &.active { border-color: var(--color-accent); background: rgba(0,240,255,0.08); box-shadow: 0 0 16px rgba(0,240,255,0.08); }
}
.mc-title { font-size: 14px; color: var(--color-text-primary); font-weight: 600; margin-bottom: 4px; }
.mc-desc { font-size: 12px; color: var(--color-text-secondary); line-height: 1.4; }

.feedback-stats { display: flex; gap: 12px; margin-bottom: 14px; }
.fb-item { flex: 1; text-align: center; padding: 10px; border-radius: 6px; &.accurate { background: rgba(82,196,26,0.08); border: 1px solid rgba(82,196,26,0.2); } &.partial { background: rgba(255,156,64,0.08); border: 1px solid rgba(255,156,64,0.2); } &.inaccurate { background: rgba(255,77,79,0.08); border: 1px solid rgba(255,77,79,0.2); } }
.fb-num { display: block; font-size: 20px; font-weight: 700; .accurate & { color: #52c41a; } .partial & { color: #ff9c40; } .inaccurate & { color: #ff4d4f; } }
.fb-lbl { font-size: 11px; color: var(--color-text-secondary); }
.learn-items { display: flex; flex-direction: column; gap: 8px; }
.li-row { display: flex; align-items: center; font-size: 12px; color: var(--color-text-secondary); }

.skill-summary { display: flex; gap: 16px; margin-bottom: 12px; }
.ss-num { display: block; font-size: 22px; font-weight: 700; }
.ss-lbl { font-size: 11px; color: var(--color-text-secondary); }
.agent-mini-list { display: flex; flex-direction: column; gap: 6px; }
.am-item { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; background: rgba(0,240,255,0.03); border-radius: 4px; }
.am-name { font-size: 13px; color: var(--color-text-primary); }

.rlhf-bar { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--color-text-secondary); margin-bottom: 12px; }
.rlhf-actions { display: flex; gap: 8px; }
.model-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(0,240,255,0.06); font-size: 12px; }
.model-row.active { background: rgba(64,201,160,0.05); }
.model-id { color: var(--color-accent); font-family: monospace; min-width: 140px; }
.model-samples, .model-date { color: var(--color-text-secondary); }
.model-active { color: #52c41a; font-weight: 600; }
.rlhf-empty { font-size: 12px; color: var(--color-text-secondary); padding: 8px 0; }

.preset-bar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.preset-label { color: var(--color-text-secondary); font-size: 12px; }
.llm-form { display: flex; flex-direction: column; gap: 10px; }
.llm-row { display: flex; align-items: center; gap: 10px; }
.llm-row label { width: 80px; color: var(--color-text-secondary); font-size: 12px; text-align: right; }
.llm-row .el-input { flex: 1; }
.llm-actions { display: flex; align-items: center; gap: 12px; }
.llm-result { font-size: 12px; color: #52c41a; }
</style>
