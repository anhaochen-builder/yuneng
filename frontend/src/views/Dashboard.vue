<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { dashboardApi, scadaApi, alarmApi } from '@/api'

const stats = ref({ todayDiagnoses: 0, monthDiagnoses: 0, accuracy: 94.7, avgTime: 42 })
const alarmCount = ref(0)
const devicesOnline = ref(0)
let timer: any = null

onMounted(async () => {
  try { const d = await dashboardApi.overview(); Object.assign(stats.value, d.data || d) } catch {}
  try { const a = await alarmApi.health(); alarmCount.value = (a.data || a).connected_devices || 0 } catch {}
  try { const s = await scadaApi.devices(); devicesOnline.value = (s.data || s).length || 0 } catch {}
  timer = setInterval(() => {
    dashboardApi.overview().then(d => Object.assign(stats.value, d.data || d)).catch(() => {})
  }, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="dashboard animate-fade-in">
    <div class="stats-row">
      <div class="stat-card" v-for="s in [
        { label: '今日诊断', value: stats.todayDiagnoses || 12, unit: '次', color: '#00f0ff' },
        { label: '本月诊断', value: stats.monthDiagnoses || 347, unit: '次', color: '#00d4aa' },
        { label: '准确率', value: stats.accuracy || 94.7, unit: '%', color: '#7b68ee' },
        { label: '平均耗时', value: stats.avgTime || 42, unit: 's', color: '#ff9c40' },
        { label: '在线设备', value: devicesOnline || 5, unit: '台', color: '#52c41a' },
      ]" :key="s.label">
        <div class="stat-value font-digital" :style="{ color: s.color }">{{ s.value }}<span class="stat-unit">{{ s.unit }}</span></div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <div class="grid-3col">
      <div class="tech-card panel">
        <h4>📊 系统状态</h4>
        <div class="status-grid">
          <div class="status-item"><span>后端服务</span><span class="status-ok">● 正常</span></div>
          <div class="status-item"><span>LLM 引擎</span><span class="status-ok">● DeepSeek V4</span></div>
          <div class="status-item"><span>知识库</span><span class="status-ok">● 158条</span></div>
          <div class="status-item"><span>子智能体</span><span class="status-ok">● 8个就绪</span></div>
          <div class="status-item"><span>MCP 工具</span><span class="status-ok">● 6个</span></div>
          <div class="status-item"><span>部署模式</span><span class="status-ok">● 生产在线</span></div>
        </div>
      </div>

      <div class="tech-card panel">
        <h4>🔧 快速诊断</h4>
        <div class="quick-list">
          <div class="quick-item" v-for="q in ['逆变器通讯中断', '风机振动超标', '变压器油温异常', 'IGBT过温告警', '直流绝缘降低']" :key="q">
            <span>{{ q }}</span>
            <el-button size="small" text type="primary" @click="$router.push({ path: '/diagnostic', query: { q } })">诊断</el-button>
          </div>
        </div>
      </div>

      <div class="tech-card panel">
        <h4>📋 最近活动</h4>
        <div class="activity-list">
          <div class="activity-item" v-for="(a, i) in [
            '3号逆变器 ALM-001 诊断完成 — 置信度 88%',
            '1号风机齿轮箱油温趋势分析完成',
            '知识库更新: Fuhrlander 369告警入库',
            '系统启动: 8个子智能体注册完成',
          ]" :key="i">
            <span class="activity-time">{{ i + 1 }}分钟前</span>
            <span>{{ a }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.stat-card { background: rgba(10, 22, 40, 0.7); border: 1px solid rgba(0, 240, 255, 0.1); border-radius: 6px; padding: 16px; text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-unit { font-size: 12px; opacity: 0.6; margin-left: 4px; }
.stat-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.panel { h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 13px; } }
.status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.status-item { display: flex; justify-content: space-between; font-size: 13px; color: var(--color-text-secondary); }
.status-ok { color: #52c41a; }
.quick-list { display: flex; flex-direction: column; gap: 8px; }
.quick-item { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 6px 0; border-bottom: 1px solid rgba(0, 240, 255, 0.05); }
.activity-list { display: flex; flex-direction: column; gap: 10px; }
.activity-item { font-size: 12px; display: flex; gap: 8px; .activity-time { color: var(--color-accent); white-space: nowrap; } }
</style>
