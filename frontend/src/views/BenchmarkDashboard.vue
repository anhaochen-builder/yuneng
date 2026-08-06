<template>
  <div class="benchmark-page">
    <div class="page-header">
      <h2>诊断准确率 Benchmark</h2>
      <div class="actions">
        <button class="btn-primary" @click="runEval" :disabled="running">{{ running ? '评测中...' : '运行规则引擎评测' }}</button>
        <select v-model="filterDevice" @change="loadCases">
          <option value="">全部设备</option>
          <option v-for="d in devices" :key="d" :value="d">{{ d }}</option>
        </select>
        <select v-model="evalLimit">
          <option :value="0">全部案例</option>
          <option :value="5">5条</option>
          <option :value="10">10条</option>
          <option :value="20">20条</option>
        </select>
      </div>
    </div>

    <div v-if="lastResult.summary" class="result-summary">
      <div class="metric-card">
        <span class="metric-value">{{ (lastResult.summary.accuracy * 100).toFixed(1) }}%</span>
        <span class="metric-label">精确匹配率</span>
      </div>
      <div class="metric-card">
        <span class="metric-value">{{ (lastResult.summary.combined_hit_rate * 100).toFixed(1) }}%</span>
        <span class="metric-label">综合命中率</span>
      </div>
      <div class="metric-card">
        <span class="metric-value">{{ lastResult.summary.total }}</span>
        <span class="metric-label">总案例</span>
      </div>
      <div class="metric-card">
        <span class="metric-value">{{ lastResult.summary.avg_latency_ms }}ms</span>
        <span class="metric-label">平均延迟</span>
      </div>
    </div>

    <div v-if="lastResult.by_device" class="device-chart">
      <h3>按设备类型</h3>
      <div v-for="(stats, dev) in lastResult.by_device" :key="dev" class="bar-row">
        <span class="bar-label">{{ dev }}</span>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: (stats.accuracy * 100) + '%' }" :class="barClass(stats.accuracy)"></div>
        </div>
        <span class="bar-value">{{ (stats.accuracy * 100).toFixed(0) }}% ({{ stats.correct }}/{{ stats.total }})</span>
      </div>
    </div>

    <div v-if="lastResult.details" class="detail-table">
      <h3>详细结果</h3>
      <table>
        <thead><tr><th>ID</th><th>设备</th><th>期望根因</th><th>预测根因</th><th>匹配</th><th>置信度</th><th>延迟</th></tr></thead>
        <tbody>
          <tr v-for="d in lastResult.details" :key="d.id" :class="'hit-' + d.hit">
            <td>{{ d.id }}</td><td>{{ d.device }}</td>
            <td class="cause-cell">{{ d.expected }}</td>
            <td class="cause-cell">{{ d.predicted?.slice(0, 80) || '-' }}</td>
            <td><span class="hit-tag" :class="d.hit">{{ hitLabel(d.hit) }}</span></td>
            <td>{{ d.confidence ? (d.confidence * 100).toFixed(0) + '%' : '-' }}</td>
            <td>{{ d.latency_ms }}ms</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="case-list">
      <h3>基准案例 ({{ cases.length }})</h3>
      <div v-for="c in cases" :key="c.id" class="case-card">
        <span class="case-id">{{ c.id }}</span>
        <span class="case-device">{{ c.device_type }}</span>
        <span :class="'risk-' + c.risk_level.toLowerCase()">{{ riskLabel(c.risk_level) }}</span>
        <span class="case-symptoms">{{ c.symptoms.slice(0, 120) }}...</span>
        <span class="case-expected">{{ c.expected_root_cause }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { riskLabel } from '@/utils/labels'

interface CaseItem { id: string; device_type: string; device_id: string; symptoms: string; expected_root_cause: string; risk_level: string }
interface DetailItem { id: string; device: string; expected: string; predicted: string; hit: string; confidence: number; latency_ms: number }
interface Summary { accuracy: number; combined_hit_rate: number; total: number; avg_latency_ms: number }
interface Result { summary?: Summary; details?: DetailItem[]; by_device?: Record<string, { accuracy: number; correct: number; total: number }> }

const cases = ref<CaseItem[]>([])
const devices = ref<string[]>([])
const lastResult = ref<Result>({})
const running = ref(false)
const filterDevice = ref('')
const evalLimit = ref(0)

function hitLabel(h: string) { return { exact: '精确', partial: '部分', miss: '未命中' }[h] || h }
function barClass(a: number) { return a >= 0.8 ? 'good' : a >= 0.5 ? 'mid' : 'bad' }

async function loadCases() {
  const params = new URLSearchParams()
  if (filterDevice.value) params.set('device', filterDevice.value)
  const { data } = await api.get('/api/benchmark?' + params.toString())
  const d = (data as { data: { cases: CaseItem[]; devices: string[]; last_result?: Summary } }).data
  cases.value = d.cases
  devices.value = d.devices
  if (d.last_result) lastResult.value = { summary: d.last_result }
}

async function runEval() {
  running.value = true
  try {
    const { data } = await api.post('/api/benchmark/run', { device: filterDevice.value, limit: evalLimit.value })
    lastResult.value = (data as { data: Result }).data
  } finally { running.value = false }
}

async function loadResult() {
  try {
    const { data } = await api.get('/api/benchmark/result')
    lastResult.value = (data as { data: Result }).data
  } catch {}
}

onMounted(() => { loadCases(); loadResult() })
</script>

<style scoped>
.benchmark-page { max-width: 1200px; margin: 0 auto; padding: 24px; color: #e0e0e0; overflow-y: auto; max-height: calc(100vh - 140px); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { color: #2FA7D1; margin: 0; font-size: 1.3em; }
.actions { display: flex; gap: 10px; align-items: center; }
.actions select { padding: 6px 10px; background: #0A1628; border: 1px solid #1E3A5F; color: #8EA8C8; border-radius: 4px; }
.btn-primary { padding: 8px 18px; background: #2FA7D1; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.result-summary { display: flex; gap: 16px; margin-bottom: 20px; }
.metric-card { flex: 1; background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 16px; text-align: center; }
.metric-value { display: block; font-size: 1.8em; font-weight: 700; color: #2FA7D1; font-family: monospace; }
.metric-label { display: block; font-size: 0.75em; color: #5A7A9A; margin-top: 4px; }

.device-chart { background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
.device-chart h3, .detail-table h3, .case-list h3 { color: #2FA7D1; font-size: 0.95em; margin-bottom: 12px; }
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.bar-label { width: 80px; color: #8EA8C8; font-size: 0.85em; text-align: right; }
.bar-track { flex: 1; height: 20px; background: #0A1628; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.bar-fill.good { background: #40C9A0; } .bar-fill.mid { background: #F0A040; } .bar-fill.bad { background: #E85555; }
.bar-value { width: 90px; font-size: 0.8em; color: #8EA8C8; }

.detail-table { background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 16px; margin-bottom: 16px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.82em; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #1E3A5F; }
th { color: #2FA7D1; font-weight: 600; }
.cause-cell { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hit-tag { padding: 2px 8px; border-radius: 3px; font-size: 0.75em; }
.hit-tag.exact { background: rgba(64,201,160,0.2); color: #40C9A0; }
.hit-tag.partial { background: rgba(240,160,64,0.2); color: #F0A040; }
.hit-tag.miss { background: rgba(232,85,85,0.2); color: #E85555; }
.hit-miss { background: rgba(232,85,85,0.05); }

.case-list { background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 16px; }
.case-card { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(30,58,95,0.5); font-size: 0.82em; }
.case-id { color: #2FA7D1; font-family: monospace; min-width: 40px; }
.case-device { color: #8EA8C8; min-width: 60px; }
.case-symptoms { flex: 1; color: #A0B8D0; }
.case-expected { color: #40C9A0; min-width: 120px; font-size: 0.85em; }
.risk-critical, .risk-high, .risk-medium, .risk-low { padding: 2px 6px; border-radius: 3px; font-size: 0.7em; }
.risk-critical { background: #E85555; color: #fff; }
.risk-high { background: rgba(240,160,64,0.3); color: #F0A040; }
.risk-medium { background: rgba(47,167,209,0.3); color: #2FA7D1; }
.risk-low { background: rgba(64,201,160,0.2); color: #40C9A0; }
</style>
