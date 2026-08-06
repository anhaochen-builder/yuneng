<template>
  <div class="shift-page">
    <div class="page-header">
      <h2>📋 交接班报告</h2>
      <div class="header-actions">
        <el-button size="small" type="primary" @click="loadReport">刷新报告</el-button>
        <el-button size="small" @click="exportReport">导出 TXT</el-button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card"><span class="sv">{{ report.stats?.total_alarms || 0 }}</span><span class="sl">本班告警</span></div>
      <div class="stat-card warn"><span class="sv">{{ report.stats?.total_diagnoses || 0 }}</span><span class="sl">触发诊断</span></div>
      <div class="stat-card danger"><span class="sv">{{ report.stats?.critical || 0 }}</span><span class="sl">高危诊断</span></div>
      <div class="stat-card"><span class="sv">{{ report.stats?.pending_orders || 0 }}</span><span class="sl">待处理工单</span></div>
    </div>

    <div class="shift-body tech-card" v-if="report.summary">
      <pre class="report-text">{{ report.summary }}</pre>
    </div>

    <div class="grid-2col">
      <div class="tech-card">
        <h4>🛡 安全措施速查</h4>
        <div v-for="(rules, dtype) in safetyRules" :key="dtype" class="sr-group">
          <span class="sr-type">{{ dtype }}</span>
          <div v-for="(r, i) in rules" :key="i" class="sr-rule">{{ r }}</div>
        </div>
      </div>
      <div class="tech-card">
        <h4>🌤 气象数据</h4>
        <div v-if="weather" class="weather-text">{{ weather }}</div>
        <div v-else class="empty-note">点击刷新获取气象数据</div>
        <el-button size="small" @click="loadWeather" style="margin-top:10px">获取气象</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const report = ref<{ summary?: string; shift_start?: string; shift_end?: string; stats?: any }>({})
const safetyRules = ref<Record<string, string[]>>({})
const weather = ref('')

onMounted(() => { loadReport(); loadSafety(); loadWeather() })

async function loadReport() {
  try {
    const r = await api.get('/api/field/shift-report')
    report.value = (r.data as any).data || r.data
  } catch {}
}

async function loadSafety() {
  try {
    const r = await api.get('/api/field/safety-rules')
    safetyRules.value = (r.data as any).data?.rules || {}
  } catch {}
}

async function loadWeather() {
  try {
    const r = await api.get('/api/field/weather')
    const d = (r.data as any)?.data || r.data
    weather.value = d?.temp && d?.desc
      ? `${d.temp}°C  ${d.desc}  |  湿度 ${d.humidity}%  |  风速 ${d.wind} km/h`
      : (d?.context || '暂无数据')
  } catch {}
}

function exportReport() {
  if (!report.value.summary) return
  const blob = new Blob(['\uFEFF' + report.value.summary], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = `交接班报告_${new Date().toISOString().slice(0, 10)}.txt`; a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.shift-page { padding: 16px; overflow-y: auto; height: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { color: #2FA7D1; margin: 0; font-size: 1.2em; }
.header-actions { display: flex; gap: 8px; }
.stats-row { display: flex; gap: 12px; margin-bottom: 14px; }
.stat-card { flex: 1; background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 14px; text-align: center; }
.stat-card.warn { border-color: rgba(240,160,64,0.3); }
.stat-card.danger { border-color: rgba(232,85,85,0.3); }
.sv { display: block; font-size: 1.6em; font-weight: 700; color: #2FA7D1; }
.sl { font-size: 0.8em; color: #8EA8C8; margin-top: 4px; display: block; }
.shift-body { margin-bottom: 14px; }
.report-text { color: #A0B8D0; font-size: 14px; line-height: 1.8; white-space: pre-wrap; margin: 0; font-family: inherit; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
h4 { color: #2FA7D1; margin-bottom: 12px; font-size: 14px; }
.sr-group { margin-bottom: 10px; }
.sr-type { display: block; color: #2FA7D1; font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.sr-rule { color: #E85555; font-size: 12px; padding: 2px 0; }
.weather-text { color: #A0B8D0; font-size: 13px; line-height: 1.7; white-space: pre-wrap; }
.empty-note { text-align: center; color: #5A7A9A; padding: 20px; }
</style>
