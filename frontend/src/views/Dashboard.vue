<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, reactive } from 'vue'
import * as echarts from 'echarts'
const loading = ref(true)
let charts: echarts.ECharts[] = []
let refreshTimer: ReturnType<typeof setInterval> | null = null

const stats = reactive({
  onlineDevices: 5, totalDevices: 9,
  todayDiagnoses: 12, monthDiagnoses: 347,
  accuracy: 94.7, avgResponseTime: 3.2,
  uptime: '99.7%', alertsToday: 6,
})

const alarmTypes = ref<Array<{ name: string; value: number; color: string }>>([
  { name: '通讯中断', value: 42, color: '#2FA7D1' },
  { name: '温度异常', value: 31, color: '#F0C040' },
  { name: '振动超标', value: 22, color: '#E85555' },
  { name: '绝缘降低', value: 15, color: '#8B80F0' },
])

const animStats = reactive({
  onlineDevices: 0, totalDevices: 9,
  todayDiagnoses: 0, accuracy: 0, avgResponseTime: 0,
})

function animateCounter(key: string, target: number, duration = 1200) {
  const start = (animStats as any)[key] || 0
  const steps = 40
  const inc = (target - start) / steps
  let step = 0
  const timer = setInterval(() => {
    step++
    if (step >= steps) { (animStats as any)[key] = target; clearInterval(timer) }
    else { (animStats as any)[key] = start + inc * step }
  }, duration / steps)
}

async function loadData() {
  try { const r = await import('@/api').then(m => m.dashboardApi.overview()); Object.assign(stats, r.data || r) } catch {}
  alarmTypes.value = [
    { name: '通讯中断', value: Math.floor(Math.random() * 15 + 38), color: '#2FA7D1' },
    { name: '温度异常', value: Math.floor(Math.random() * 12 + 25), color: '#F0C040' },
    { name: '振动超标', value: Math.floor(Math.random() * 8 + 18), color: '#E85555' },
    { name: '绝缘降低', value: Math.floor(Math.random() * 6 + 9), color: '#8B80F0' },
  ]
  animateCounter('onlineDevices', stats.onlineDevices || 5)
  animateCounter('todayDiagnoses', stats.todayDiagnoses || 12)
  animateCounter('accuracy', stats.accuracy || 94.7)
  animateCounter('avgResponseTime', stats.avgResponseTime || 3.2)
}

onMounted(async () => {
  await loadData()
  loading.value = false
  initCharts()
  window.addEventListener('resize', handleResize)
  refreshTimer = setInterval(loadData, 30000)
})
onUnmounted(() => {
  charts.forEach(c => c.dispose())
  window.removeEventListener('resize', handleResize)
  if (refreshTimer) clearInterval(refreshTimer)
})
function handleResize() { charts.forEach(c => c.resize()) }

function gradientFrom(top: string, bottom: string): any[] {
  return [{ offset: 0, color: top }, { offset: 1, color: bottom }]
}

function initCharts() {
  nextTick(() => {
    charts.forEach(c => c.dispose())
    charts = []
    const commonGrid = { top: 32, right: 12, bottom: 20, left: 42 }

    // ═══ 左列 ═══
    // 模块1: 近7日诊断趋势
    const m1 = echarts.init(document.getElementById('m1')!)
    m1.setOption({
      grid: { ...commonGrid },
      xAxis: { type: 'category', data: ['周一','周二','周三','周四','周五','周六','周日'], boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(10,84,150,0.3)' } },
        axisLabel: { color: '#8ba0c8', fontSize: 10 } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(47,167,209,0.08)' } },
        axisLabel: { color: '#8ba0c8', fontSize: 10 } },
      series: [{
        type: 'line', smooth: true, symbol: 'circle', symbolSize: 7,
        data: [8, 12, 9, 15, 11, 14, 12],
        lineStyle: { width: 3, color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientFrom('#2FA7D1', '#8B80F0')) },
        itemStyle: { color: '#2FA7D1', borderColor: 'rgba(0,240,255,0.4)', borderWidth: 2 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, gradientFrom('rgba(47,167,209,0.3)', 'rgba(47,167,209,0)')) },
        markLine: { silent: true, symbol: 'none', label: { formatter: '均值 11.6', color: '#8B80F0', fontSize: 10 },
          lineStyle: { color: '#8B80F0', type: 'dashed', width: 1 }, data: [{ yAxis: 11.6 }] }
      }]
    })
    charts.push(m1)

    // 模块2: 24h诊断频次
    const m2 = echarts.init(document.getElementById('m2')!)
    const hours = Array.from({length:12},(_,i)=>`${i*2}:00`)
    const hourData = [2,5,3,7,4,8,6,12,9,10,7,5]
    m2.setOption({
      grid: { ...commonGrid },
      xAxis: { type: 'category', data: hours,
        axisLine: { lineStyle: { color: 'rgba(10,84,150,0.3)' } },
        axisLabel: { color: '#8ba0c8', fontSize: 10 } },
      yAxis: { type: 'value', splitLine: { show: false },
        axisLabel: { color: '#8ba0c8', fontSize: 10 } },
      series: [{
        type: 'bar', data: hourData, barWidth: '14',
        itemStyle: {
          borderRadius: [3, 3, 0, 0],
          color: (p: any) => new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: p.value > 10 ? '#40E0D0' : '#2FA7D1' },
            { offset: 1, color: 'rgba(47,167,209,0.1)' }])
        },
        emphasis: { itemStyle: { color: '#40E0D0' } }
      }]
    })
    charts.push(m2)

    // 模块3: Judge评分趋势
    const m3 = echarts.init(document.getElementById('m3')!)
    m3.setOption({
      grid: { ...commonGrid },
      xAxis: { type: 'category', data: hours, boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(10,84,150,0.3)' } },
        axisLabel: { color: '#8ba0c8', fontSize: 10 } },
      yAxis: { type: 'value', min: 50, max: 100,
        splitLine: { lineStyle: { color: 'rgba(255,156,64,0.08)' } },
        axisLabel: { color: '#8ba0c8', fontSize: 10 } },
      series: [{
        type: 'line', smooth: true, symbol: 'diamond', symbolSize: 6,
        data: [82,78,85,72,88,92,87,90,84,89,93,91],
        lineStyle: { width: 2.5, color: '#ff9c40' },
        itemStyle: { color: '#ff9c40' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, gradientFrom('rgba(255,156,64,0.25)', 'rgba(255,156,64,0)')) },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: '#E85555', type: 'dashed', width: 1 },
          label: { formatter: '阈值70', color: '#E85555', fontSize: 10 }, data: [{ yAxis: 70 }] }
      }]
    })
    charts.push(m3)

    // ═══ 右列 ═══
    // 模块4: 设备状态分布
    const m4 = echarts.init(document.getElementById('m4')!)
    const online = 6; const alarmC = 2; const fault = 1
    m4.setOption({
      tooltip: { trigger: 'item', backgroundColor: 'rgba(4,32,79,0.95)', borderColor: '#2FA7D1' },
      legend: { bottom: 2, textStyle: { color: '#8ba0c8', fontSize: 10 }, itemWidth: 8, itemHeight: 8 },
      series: [{
        type: 'pie', radius: ['58%', '76%'], center: ['50%', '45%'],
        label: { show: false },
        emphasis: { scaleSize: 8, label: { show: true, fontSize: 13 } },
        data: [
          { value: online, name: '运行中', itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, gradientFrom('#40E0D0', '#1a8a7a')) } },
          { value: alarmC, name: '告警', itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, gradientFrom('#F0C040', '#b8921e')) } },
          { value: fault, name: '故障', itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, gradientFrom('#E85555', '#9e2424')) } },
        ]
      }],
      graphic: { elements: [{ type: 'text', left: 'center', top: '38%', style: { text: `${online+alarmC+fault}\n设备`, textAlign: 'center', fill: '#fff', fontSize: 15, fontWeight: 'bold', lineHeight: 20 } }] }
    })
    charts.push(m4)

    // 模块5: 告警类型分布
    const m5 = echarts.init(document.getElementById('m5')!)
    const alarmData = alarmTypes.value
    m5.setOption({
      tooltip: { trigger: 'item', backgroundColor: 'rgba(4,32,79,0.95)', borderColor: '#F0C040' },
      series: [{
        type: 'pie', radius: ['65%', '82%'], center: ['50%', '48%'],
        label: { show: true, position: 'outside', formatter: '{b}\n{d}%', color: '#8ba0c8', fontSize: 9 },
        labelLine: { lineStyle: { color: 'rgba(139,160,200,0.25)' } },
        itemStyle: { borderRadius: 3, borderColor: 'rgba(3,14,35,0.5)', borderWidth: 1.5 },
        data: alarmData.map(a => ({ value: a.value, name: a.name, itemStyle: { color: a.color } }))
      }]
    })
    charts.push(m5)

    // 模块6: 各阶段响应耗时
    const m6 = echarts.init(document.getElementById('m6')!)
    m6.setOption({
      grid: { ...commonGrid, bottom: 10 },
      xAxis: { type: 'value', max: 8, splitLine: { lineStyle: { color: 'rgba(10,84,150,0.08)' } },
        axisLabel: { color: '#8ba0c8', fontSize: 10, formatter: '{value}s' } },
      yAxis: { type: 'category', axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#8ba0c8', fontSize: 10 },
        data: ['SCADA采集', '图像分析', 'RAG检索', 'LLM推理', '诊断输出'] },
      series: [{
        type: 'bar', barWidth: 14,
        label: { show: true, position: 'right', color: '#8ba0c8', fontSize: 10, formatter: '{c}s' },
        data: [
          { value: 3.2, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientFrom('#2FA7D1', '#40E0D0')) } },
          { value: 2.1, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientFrom('#8B80F0', '#B8AFFF')) } },
          { value: 1.5, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientFrom('#F0C040', '#FFE080')) } },
          { value: 4.8, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientFrom('#ff9c40', '#FFB380')) } },
          { value: 0.8, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientFrom('#40C9A0', '#80E8C0')) } },
        ],
        emphasis: { itemStyle: { shadowBlur: 16, shadowColor: 'rgba(47,167,209,0.35)' } }
      }]
    })
    charts.push(m6)
  })
}
</script>

<template>
  <div class="dashboard-root" v-loading="loading">
    <!-- KPI 顶部栏 -->
    <div class="kpi-row">
      <div class="kpi-card" v-for="(kpi, idx) in [
        { label: '运行设备', val: animStats.onlineDevices as any, total: stats.totalDevices, color: '#40E0D0', icon: '📡' },
        { label: '今日诊断', val: animStats.todayDiagnoses as any, total: 0, unit: '次', color: '#2FA7D1', icon: '🔍' },
        { label: '准确率', val: animStats.accuracy as any, unit: '%', color: '#8B80F0', icon: '🎯' },
        { label: '响应时间', val: animStats.avgResponseTime as any, unit: 's', color: '#F0C040', icon: '⚡' },
        { label: '运行时间', val: stats.uptime as any, color: '#40C9A0', icon: '🛡' },
      ]" :key="idx">
        <span class="kpi-icon" :style="{color:kpi.color}">{{ kpi.icon }}</span>
        <div class="kpi-right">
          <div class="kpi-val font-digital" :style="{color:kpi.color}">
            <template v-if="kpi.label==='运行设备'">{{ Math.round(animStats.onlineDevices) }}<span class="kpi-total">/{{stats.totalDevices}}</span></template>
            <template v-else-if="kpi.label==='运行时间'">{{ stats.uptime }}</template>
            <template v-else-if="typeof kpi.val==='string'">{{ kpi.val }}</template>
            <template v-else>{{ kpi.val.toFixed(kpi.label==='响应时间'?1:0) }}</template>
          </div>
          <div class="kpi-lbl">{{ kpi.label }}</div>
        </div>
        <div class="kpi-bar" v-if="kpi.label!=='运行时间'">
          <div class="kpi-bar-fill" :style="{width: (kpi.label==='运行设备'?animStats.onlineDevices/stats.totalDevices*100:kpi.label==='准确率'?animStats.accuracy:kpi.label==='响应时间'?68:50)+'%',background:kpi.color}"></div>
        </div>
      </div>
    </div>

    <!-- 三栏: 左3 + 中空 + 右3 -->
    <div class="main-grid">
      <!-- 左列: 3个模块 -->
      <div class="side-col">
        <div class="viz-panel">
          <div class="vp-hdr"><span>📈 近7日诊断趋势</span><span class="vp-badge">本月 {{stats.monthDiagnoses||347}}次</span></div>
          <div id="m1" class="chart-box"></div>
        </div>
        <div class="viz-panel">
          <div class="vp-hdr"><span>🕐 24h诊断频次</span><span class="vp-badge">峰值 12 次</span></div>
          <div id="m2" class="chart-box"></div>
        </div>
        <div class="viz-panel">
          <div class="vp-hdr"><span>🎯 Judge评分趋势</span><span class="vp-badge green">质量良好</span></div>
          <div id="m3" class="chart-box"></div>
        </div>
      </div>

      <!-- 中间: 漂浮参数块 -->
      <div class="center-col">
        <div class="float-blocks">
          <div class="fb fb-1" style="top:14%;left:10%">
            <div class="fb-glow" style="background:radial-gradient(ellipse at center, rgba(64,224,208,0.2) 0%, transparent 70%)"></div>
            <div class="fb-title">模型引擎</div>
            <div class="fb-val font-digital" style="color:#40E0D0">DeepSeek V4</div>
          </div>
          <div class="fb fb-2" style="top:28%;right:8%">
            <div class="fb-glow" style="background:radial-gradient(ellipse at center, rgba(139,128,240,0.2) 0%, transparent 70%)"></div>
            <div class="fb-title">子智能体</div>
            <div class="fb-val font-digital" style="color:#8B80F0">8</div>
            <div class="fb-sub">全部就绪</div>
          </div>
          <div class="fb fb-3" style="top:50%;left:12%">
            <div class="fb-glow" style="background:radial-gradient(ellipse at center, rgba(240,192,64,0.18) 0%, transparent 70%)"></div>
            <div class="fb-title">知识条目</div>
            <div class="fb-val font-digital" style="color:#F0C040">160</div>
            <div class="fb-sub">持续累积中</div>
          </div>
          <div class="fb fb-4" style="top:52%;right:14%">
            <div class="fb-glow" style="background:radial-gradient(ellipse at center, rgba(47,167,209,0.2) 0%, transparent 70%)"></div>
            <div class="fb-title">MCP工具</div>
            <div class="fb-val font-digital" style="color:#2FA7D1">6</div>
            <div class="fb-sub">全部就绪</div>
          </div>
          <div class="fb fb-5" style="top:68%;left:18%">
            <div class="fb-glow" style="background:radial-gradient(ellipse at center, rgba(64,201,154,0.18) 0%, transparent 70%)"></div>
            <div class="fb-title">Hook拦截器</div>
            <div class="fb-val font-digital" style="color:#40C9A0">12</div>
            <div class="fb-sub">全部激活</div>
          </div>
        </div>
      </div>

      <!-- 右列: 3个模块 -->
      <div class="side-col">
        <div class="viz-panel">
          <div class="vp-hdr"><span>⚙️ 设备状态分布</span><span class="vp-badge green">在线率 {{((stats.onlineDevices||5)/(stats.totalDevices||9)*100).toFixed(0)}}%</span></div>
          <div id="m4" class="chart-box"></div>
        </div>
        <div class="viz-panel">
          <div class="vp-hdr"><span>🚨 告警类型分布</span><span class="vp-badge orange">今日 {{stats.alertsToday||6}}条</span></div>
          <div id="m5" class="chart-box"></div>
        </div>
        <div class="viz-panel">
          <div class="vp-hdr"><span>⏱ 各阶段响应耗时</span><span class="vp-badge">均值 {{stats.avgResponseTime||3.2}}s</span></div>
          <div id="m6" class="chart-box"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dashboard-root {
  height: 100%; display: flex; flex-direction: column;
  gap: 8px; padding: 4px 16px;
  overflow: hidden;
}

// ── KPI ──
.kpi-row {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
  flex-shrink: 0; z-index: 1;
}
.kpi-card {
  position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(6,30,65,0.65) 0%, rgba(8,36,70,0.35) 100%);
  border: 1px solid rgba(0,240,255,0.1);
  border-radius: 8px;
  transition: all 0.3s;
  &:hover { border-color: rgba(0,240,255,0.25); transform: translateY(-1px); }
}
.kpi-icon { font-size: 22px; flex-shrink: 0; }
.kpi-right { flex: 1; z-index: 1; }
.kpi-val { font-size: 22px; font-weight: 700; }
.kpi-total { font-size: 13px; font-weight: 400; color: #8ba0c8; margin-left: 2px; }
.kpi-lbl { font-size: 10px; color: #8ba0c8; margin-top: 1px; letter-spacing: 0.5px; }
.kpi-bar { position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: rgba(255,255,255,0.04); }
.kpi-bar-fill { height: 100%; transition: width 1.5s cubic-bezier(0.4,0,0.2,1); opacity: 0.5; }

// ── 主网格 ──
.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  flex: 1; gap: 10px;
  min-height: 0; z-index: 1;
}
.side-col { display: flex; flex-direction: column; gap: 8px; }
.center-col {
  position: relative;
  overflow: hidden;
  pointer-events: none;
}

// ── 漂浮参数块 (玻璃质感) ──
.float-blocks {
  position: absolute; inset: 0;
}
.fb {
  position: absolute;
  padding: 14px 18px;
  background: rgba(4, 24, 56, 0.35);
  border: 1px solid rgba(47, 167, 209, 0.15);
  border-radius: 12px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  min-width: 120px;
  overflow: hidden;
  animation: fbFloat 7s ease-in-out infinite;
  pointer-events: auto;
  cursor: default;
  transition: border-color 0.4s, box-shadow 0.4s, background 0.4s;
  &:hover {
    background: rgba(4, 28, 64, 0.5);
    border-color: rgba(47, 167, 209, 0.35);
    box-shadow: 0 0 30px rgba(0, 120, 200, 0.12), inset 0 1px 0 rgba(47,167,209,0.08);
  }
}
.fb-glow {
  position: absolute; inset: 0; pointer-events: none;
  opacity: 0.6; animation: glowPulse 4s ease-in-out infinite;
}
@keyframes glowPulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.7; }
}
.fb-1 { animation-delay: 0s; }
.fb-2 { animation-delay: 1.8s; }
.fb-3 { animation-delay: 3.5s; }
.fb-4 { animation-delay: 5.2s; }
.fb-5 { animation-delay: 2.6s; }
@keyframes fbFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.fb-title { font-size: 10px; color: #6a88a8; letter-spacing: 1.5px; margin-bottom: 4px; text-transform: uppercase; }
.fb-val { font-size: 20px; font-weight: 700; line-height: 1.1; }
.fb-sub { font-size: 10px; color: #8ba0c8; opacity: 0.65; margin-top: 2px; }
.fb-unit { font-size: 11px; font-weight: 400; color: #8ba0c8; }
.fb-line { height: 2px; background: rgba(255,255,255,0.06); margin-top: 6px; border-radius: 1px; }
.fb-line-fill { height: 100%; border-radius: 1px; transition: width 0.8s ease; }

.viz-panel {
  flex: 1;
  background: linear-gradient(160deg, rgba(6,28,62,0.5) 0%, rgba(3,14,35,0.6) 100%);
  border: 1px solid rgba(0,240,255,0.1);
  border-radius: 8px;
  display: flex; flex-direction: column;
  padding: 8px 12px 4px;
  transition: all 0.3s;
  overflow: hidden;
  &:hover { border-color: rgba(0,240,255,0.2); box-shadow: 0 0 20px rgba(0,100,255,0.05); }
}
.vp-hdr {
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0; margin-bottom: 2px;
  span:first-child { font-size: 12px; color: #c8d8e8; font-weight: 600; }
}
.vp-badge {
  font-size: 10px; padding: 1px 8px; border-radius: 10px;
  background: rgba(47,167,209,0.12); color: var(--color-accent);
  &.green { background: rgba(64,201,154,0.12); color: #40C9A0; }
  &.orange { background: rgba(240,192,64,0.12); color: #F0C040; }
}
.chart-box { flex: 1; min-height: 0; }
</style>
