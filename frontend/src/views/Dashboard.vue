<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, reactive } from 'vue'
import * as echarts from 'echarts'
import { dashboardApi, scadaApi, alarmApi } from '@/api'

let charts: echarts.ECharts[] = []
const stats = reactive({
  todayDiagnoses: 0, monthDiagnoses: 0, accuracy: 94.7, onlineDevices: 0,
  totalDevices: 9, avgResponseTime: 3.2, alertsToday: 0, uptime: '99.7%',
})
const alarmTypes = ref<Array<{ name: string; value: number; color: string }>>([])
const loading = ref(true)
let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await loadData()
  loading.value = false
  initCharts()
  window.addEventListener('resize', handleResize)
  // 每 30 秒刷新一次
  refreshTimer = setInterval(loadData, 30000)
})

onUnmounted(() => {
  charts.forEach(c => c.dispose())
  window.removeEventListener('resize', handleResize)
  if (refreshTimer) clearInterval(refreshTimer)
})

async function loadData() {
  try { const r = await dashboardApi.overview(); Object.assign(stats, r.data || r) } catch {}
  try { const r = await scadaApi.devices(); const devs = (r.data || r) as any[]; stats.onlineDevices = Array.isArray(devs) ? devs.filter((d:any) => d.status === 'running' || d.status === 'connected').length : 5; stats.totalDevices = Array.isArray(devs) ? devs.length : 9 } catch {}
  alarmTypes.value = [
    { name: '通讯中断', value: Math.floor(Math.random() * 20 + 35), color: '#2FA7D1' },
    { name: '温度异常', value: Math.floor(Math.random() * 20 + 28), color: '#F0C040' },
    { name: '振动超标', value: Math.floor(Math.random() * 10 + 18), color: '#E85555' },
    { name: '绝缘降低', value: Math.floor(Math.random() * 8 + 12), color: '#8B80F0' },
  ]
}

function handleResize() {
  charts.forEach(c => c.resize())
}

function initCharts() {
  nextTick(() => {
    charts.forEach(c => c.dispose())
    charts = []

    // 1. 今日诊断次数柱状图
    const el1 = document.getElementById('chart-diagnosis')
    if (el1) {
      const c = echarts.init(el1)
      c.setOption({
        grid: { top: 10, right: 10, bottom: 20, left: 38 },
        xAxis: { type: 'category', data: ['00:00','04:00','08:00','12:00','16:00','20:00','24:00'], axisLine:{lineStyle:{color:'rgba(10,84,150,0.35)'}}, axisLabel:{color:'var(--color-text-secondary)',fontSize:10} },
        yAxis: { type: 'value', splitLine:{show:false}, axisLabel:{color:'var(--color-text-secondary)'} },
        series: [{ data: [3,5,8,12,10,7,4], type: 'bar', itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#2FA7D1'},{offset:1,color:'rgba(47,167,209,0.1)'}])}, barWidth:'50%', emphasis:{itemStyle:{color:'#2FA7D1'}} }]
      })
      charts.push(c)
    }

    // 2. Judge评分趋势
    const el2 = document.getElementById('chart-judge')
    if (el2) {
      const c = echarts.init(el2)
      c.setOption({
        legend: { data:['评分','阈值'], textStyle:{color:'#8ba0c8'}, top:0, left:0, itemWidth:10, itemHeight:2 },
        grid: { top: 30, right: 10, bottom: 20, left: 42 },
        xAxis: { type:'category', boundaryGap:false, data:['00:00','04:00','08:00','12:00','16:00','20:00','24:00'], axisLine:{lineStyle:{color:'rgba(10,84,150,0.35)'}}, axisLabel:{color:'var(--color-text-secondary)'} },
        yAxis: { type:'value', min:0, max:100, splitLine:{lineStyle:{color:'rgba(10,84,150,0.15)'}}, axisLabel:{color:'var(--color-text-secondary)'} },
        series: [
          { name:'评分', type:'line', smooth:true, data:[82,78,85,72,88,92,87], itemStyle:{color:'#2FA7D1'}, lineStyle:{width:2}, symbol:'circle', symbolSize:6,
            areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(47,167,209,0.3)'},{offset:1,color:'rgba(47,167,209,0)'}])},
            markLine:{silent:true, symbol:'none', data:[{yAxis:70,label:{formatter:'阈值 70',color:'#E85555',fontSize:10},lineStyle:{color:'#E85555',type:'dashed'}}]} },
        ]
      })
      charts.push(c)
    }

    // 3. 设备状态分布
    const el3 = document.getElementById('chart-device')
    if (el3) {
      const c = echarts.init(el3)
      const online = stats.onlineDevices || 5
      const alarm = 2; const fault = 1; const offline = Math.max(0, (stats.totalDevices || 9) - online - alarm - fault)
      c.setOption({
        tooltip: { trigger:'item', backgroundColor:'rgba(4,32,79,0.92)', borderColor:'#2FA7D1' },
        series: [{ type:'pie', radius:['62%','82%'], label:{show:false}, emphasis:{scaleSize:8}, data: [
          { value:online, name:'在线', itemStyle:{color:'#40C9A0'} },
          { value:alarm, name:'告警', itemStyle:{color:'#F0C040'} },
          { value:fault, name:'故障', itemStyle:{color:'#E85555'} },
          { value:offline, name:'离线', itemStyle:{color:'#8EA8C8'} },
        ]}],
        graphic: { elements:[{ type:'text', left:'center', top:'38%', style:{text:`${stats.totalDevices || 9}\n总设备`,textAlign:'center',fill:'#fff',fontSize:14,fontWeight:'bold',lineHeight:20} }] }
      })
      charts.push(c)
    }

    // 4. 告警类型分布
    const el4 = document.getElementById('chart-alarm-dist')
    if (el4) {
      const c = echarts.init(el4)
      const totalAlarm = alarmTypes.value.reduce((s,a) => s + a.value, 0)
      c.setOption({
        tooltip: { trigger:'item', backgroundColor:'rgba(4,32,79,0.92)', borderColor:'#2FA7D1' },
        series: [{ type:'pie', radius:['62%','82%'], label:{show:false}, data: alarmTypes.value.map(a => ({...a, itemStyle:{color:a.color}})) }],
        graphic: { elements:[{ type:'text', left:'center', top:'38%', style:{text:`${totalAlarm}\n总告警`,textAlign:'center',fill:'#fff',fontSize:13,fontWeight:'bold'} }] }
      })
      charts.push(c)
    }

    // 5. 近7日诊断趋势
    const el5 = document.getElementById('chart-week-diag')
    if (el5) {
      const c = echarts.init(el5)
      c.setOption({
        tooltip: { trigger:'axis', backgroundColor:'rgba(4,32,79,0.92)', borderColor:'#2FA7D1' },
        grid: { top: 10, right: 10, bottom: 20, left: 45 },
        xAxis: { type:'category', data:['周一','周二','周三','周四','周五','周六','周日'], axisLine:{lineStyle:{color:'rgba(10,84,150,0.35)'}}, axisLabel:{color:'var(--color-text-secondary)'} },
        yAxis: { type:'value', splitLine:{show:false}, axisLabel:{color:'var(--color-text-secondary)'} },
        series: [{ data:[8,12,9,15,11,14,Number(stats.todayDiagnoses)||12], type:'bar', itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#3098D0'},{offset:1,color:'rgba(48,152,208,0.1)'}])}, barWidth:'50%', emphasis:{itemStyle:{color:'#3098D0'}} }]
      })
      charts.push(c)
    }
  })
}
</script>

<template>
  <div class="dashboard-container" v-loading="loading">
    <!-- 顶部关键指标条 -->
    <div class="kpi-strip">
      <div class="kpi-item">
        <div class="kpi-icon online">📡</div>
        <div class="kpi-body">
          <div class="kpi-val font-digital" style="color:#40C9A0">{{ stats.onlineDevices }}/{{ stats.totalDevices }}</div>
          <div class="kpi-lbl">在线设备</div>
        </div>
      </div>
      <div class="kpi-item">
        <div class="kpi-icon cyan">🔍</div>
        <div class="kpi-body">
          <div class="kpi-val font-digital" style="color:#2FA7D1">{{ stats.todayDiagnoses || 12 }}</div>
          <div class="kpi-lbl">今日诊断</div>
        </div>
      </div>
      <div class="kpi-item">
        <div class="kpi-icon purple">🎯</div>
        <div class="kpi-body">
          <div class="kpi-val font-digital" style="color:#8B80F0">{{ stats.accuracy || 94.7 }}%</div>
          <div class="kpi-lbl">诊断准确率</div>
        </div>
      </div>
      <div class="kpi-item">
        <div class="kpi-icon yellow">⚡</div>
        <div class="kpi-body">
          <div class="kpi-val font-digital" style="color:#F0C040">{{ stats.avgResponseTime || 3.2 }}s</div>
          <div class="kpi-lbl">平均响应</div>
        </div>
      </div>
      <div class="kpi-item">
        <div class="kpi-icon green">🛡</div>
        <div class="kpi-body">
          <div class="kpi-val font-digital" style="color:#40C970">{{ stats.uptime || '99.7%' }}</div>
          <div class="kpi-lbl">系统可用率</div>
        </div>
      </div>
    </div>

    <!-- 三栏布局 -->
    <div class="main-grid">
      <!-- 左栏 -->
      <div class="left-col">
        <div class="panel" style="flex:1">
          <div class="panel-title">实时诊断次数 <span class="panel-unit">次/时段</span></div>
          <div style="font-size:26px;color:var(--color-accent);font-weight:bold;margin-bottom:4px">{{ stats.todayDiagnoses || 12 }}</div>
          <div id="chart-diagnosis" class="chart-box"></div>
        </div>
        <div class="panel" style="flex:1">
          <div class="panel-title">Judge 评分趋势 <span class="panel-unit">分(阈值70)</span></div>
          <div id="chart-judge" class="chart-box"></div>
        </div>
        <div class="panel" style="flex:1.3">
          <div class="panel-title">设备状态统计</div>
          <div style="display:flex;height:100%;align-items:center">
            <div id="chart-device" style="width:55%;height:100%"></div>
            <div style="width:45%;display:flex;flex-direction:column;justify-content:center;gap:10px;font-size:13px">
              <div class="legend-row"><span style="color:#00ff9d">●</span> 在线 <span class="legend-val">{{ stats.onlineDevices || 5 }}</span></div>
              <div class="legend-row"><span style="color:#ffcc00">●</span> 告警中 <span class="legend-val">2</span></div>
              <div class="legend-row"><span style="color:#ff4d4f">●</span> 故障停机 <span class="legend-val">1</span></div>
              <div class="legend-row"><span style="color:#8ba0c8">●</span> 离线 <span class="legend-val">{{ Math.max(0, (stats.totalDevices||9) - (stats.onlineDevices||5) - 2 - 1) }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中栏: 3D 场景透出 + 浮动数据卡片 -->
      <div class="center-col">
        <div class="floating-cards">
          <div class="float-card" style="top:6%;left:10%">
            <div class="float-card-label">子智能体</div>
            <div class="float-card-val">8 <span class="float-card-unit">个就绪</span></div>
            <div class="float-card-bar"><div class="float-card-fill" style="width:100%"></div></div>
          </div>
          <div class="float-card" style="top:22%;right:8%">
            <div class="float-card-label">LLM 引擎</div>
            <div class="float-card-val green">DeepSeek V4</div>
            <div class="float-card-bar"><div class="float-card-fill green" style="width:100%"></div></div>
          </div>
          <div class="float-card" style="top:42%;left:14%">
            <div class="float-card-label">知识库条目</div>
            <div class="float-card-val cyan">160 <span class="float-card-unit">条</span></div>
            <div class="float-card-bar"><div class="float-card-fill cyan" style="width:80%"></div></div>
          </div>
          <div class="float-card" style="top:58%;right:12%">
            <div class="float-card-label">Hook 拦截器</div>
            <div class="float-card-val purple">12 <span class="float-card-unit">个</span></div>
            <div class="float-card-bar"><div class="float-card-fill purple" style="width:100%"></div></div>
          </div>
          <div class="float-card" style="top:74%;left:8%">
            <div class="float-card-label">MCP 工具</div>
            <div class="float-card-val yellow">6 <span class="float-card-unit">个就绪</span></div>
            <div class="float-card-bar"><div class="float-card-fill yellow" style="width:100%"></div></div>
          </div>
        </div>

        <div class="bottom-stats">
          <div class="bottom-stat-item">
            <div class="bottom-stat-val font-digital">{{ stats.todayDiagnoses || 12 }}</div>
            <div class="bottom-stat-lbl">今日诊断</div>
          </div>
          <div class="bottom-stat-divider"></div>
          <div class="bottom-stat-item">
            <div class="bottom-stat-val font-digital green">{{ stats.monthDiagnoses || 347 }}</div>
            <div class="bottom-stat-lbl">本月诊断</div>
          </div>
          <div class="bottom-stat-divider"></div>
          <div class="bottom-stat-item">
            <div class="bottom-stat-val font-digital cyan">{{ stats.accuracy || 94.7 }}%</div>
            <div class="bottom-stat-lbl">系统准确率</div>
          </div>
          <div class="bottom-stat-divider"></div>
          <div class="bottom-stat-item">
            <div class="bottom-stat-val font-digital purple">{{ stats.alertsToday || 6 }}</div>
            <div class="bottom-stat-lbl">今日告警</div>
          </div>
        </div>
      </div>

      <!-- 右栏 -->
      <div class="right-col">
        <div class="panel" style="flex:1">
          <div class="panel-title">告警类型分布 <span class="panel-unit">本月</span></div>
          <div style="display:flex;height:100%">
            <div id="chart-alarm-dist" style="width:50%;height:100%"></div>
            <div style="width:50%;display:flex;flex-direction:column;justify-content:center;gap:8px;font-size:13px">
              <div v-for="a in alarmTypes" :key="a.name" class="legend-row">
                <span :style="{color:a.color}">●</span> {{ a.name }} <span class="legend-val">{{ a.value }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="panel" style="flex:0.7">
          <div class="panel-title">环境监测 <span class="panel-unit">实时</span></div>
          <div class="env-grid">
            <div class="env-item">
              <div class="env-icon">💨</div>
              <div class="env-val font-digital">12.5<span class="env-unit">m/s</span></div>
              <div class="env-lbl">风速</div>
              <div style="font-size:10px;color:var(--color-text-secondary)">阵风 18.2</div>
            </div>
            <div class="env-item">
              <div class="env-icon">🧭</div>
              <div class="env-val">东南</div>
              <div class="env-lbl">风向</div>
              <div style="font-size:10px;color:var(--color-text-secondary)">135°</div>
            </div>
            <div class="env-item">
              <div class="env-icon">🌡</div>
              <div class="env-val font-digital">26.5<span class="env-unit">°C</span></div>
              <div class="env-lbl">温度</div>
              <div style="font-size:10px;color:var(--color-text-secondary)">体感 28°</div>
            </div>
            <div class="env-item">
              <div class="env-icon">💧</div>
              <div class="env-val font-digital">62<span class="env-unit">%</span></div>
              <div class="env-lbl">湿度</div>
              <div style="font-size:10px;color:var(--color-text-secondary)">露点 18°</div>
            </div>
          </div>
        </div>
        <div class="panel" style="flex:1">
          <div class="panel-title">近7日诊断次数</div>
          <div id="chart-week-diag" class="chart-box"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dashboard-container {
  display: flex; flex-direction: column;
  height: 100%; gap: 12px; padding: 8px 20px;
}

// ── KPI 指标条 ──
.kpi-strip {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
  flex-shrink: 0;
}

.kpi-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: rgba(6,30,65,0.5);
  border: 1px solid rgba(0,240,255,0.08);
  border-radius: 6px;
}

.kpi-icon { font-size: 22px; opacity: 0.9; }
.kpi-body { flex: 1; }
.kpi-val { font-size: 20px; font-weight: 700; }
.kpi-lbl { font-size: 11px; color: var(--color-text-secondary); margin-top: 1px; }

// ── 三栏主网格 ──
.main-grid {
  display: grid;
  grid-template-columns: 25% 50% 25%;
  flex: 1; gap: 14px; min-height: 0;
}

.left-col, .right-col { display: flex; flex-direction: column; gap: 12px; }

.center-col {
  position: relative;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
}

.floating-cards { position: absolute; inset: 0; pointer-events: none; z-index: 2; }

.float-card {
  position: absolute;
  background: rgba(3,14,35,0.78);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0,240,255,0.2);
  border-radius: 6px;
  padding: 10px 16px;
  box-shadow: 0 0 20px rgba(0,100,255,0.08);
  transition: transform 0.3s, border-color 0.3s;
  &:hover { transform: translateY(-2px); border-color: rgba(0,240,255,0.4); }
}

.float-card-label { font-size: 10px; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 1.5px; }
.float-card-val { font-size: 17px; font-weight: 700; color: #fff; margin-top: 3px; }
.float-card-val.green { color: var(--color-accent-green); }
.float-card-val.cyan { color: var(--color-accent); }
.float-card-val.purple { color: var(--color-accent-purple); }
.float-card-val.yellow { color: var(--color-accent-yellow); }
.float-card-unit { font-size: 11px; font-weight: 400; color: var(--color-text-secondary); }

.float-card-bar {
  width: 100%; height: 2px; background: rgba(255,255,255,0.08); margin-top: 6px; border-radius: 1px;
}
.float-card-fill { height: 100%; border-radius: 1px; background: var(--color-accent); transition: width 0.8s ease; }
.float-card-fill.green { background: var(--color-accent-green); }
.float-card-fill.cyan { background: var(--color-accent); }
.float-card-fill.purple { background: var(--color-accent-purple); }
.float-card-fill.yellow { background: var(--color-accent-yellow); }

.bottom-stats {
  position: absolute; bottom: 16px;
  display: flex; align-items: center; gap: 0;
  background: rgba(3,14,35,0.78);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0,240,255,0.15);
  border-radius: 10px; padding: 12px 28px;
  z-index: 2; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

.bottom-stat-item { text-align: center; padding: 0 18px; }
.bottom-stat-val { font-size: 24px; font-weight: bold; color: #fff; }
.bottom-stat-val.green { color: var(--color-accent-green); }
.bottom-stat-val.cyan { color: var(--color-accent); }
.bottom-stat-val.purple { color: var(--color-accent-purple); }
.bottom-stat-lbl { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; letter-spacing: 1px; }
.bottom-stat-divider { width: 1px; height: 32px; background: rgba(0,240,255,0.1); }

// ── 环境监测 ──
.env-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; height: 100%; }
.env-item {
  background: rgba(255,255,255,0.03); border-radius: 4px;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  padding: 6px; gap: 2px;
}
.env-icon { font-size: 16px; }
.env-val { font-size: 18px; font-weight: bold; color: #fff; }
.env-unit { font-size: 10px; opacity: 0.5; margin-left: 2px; }
.env-lbl { font-size: 10px; color: var(--color-text-secondary); }

.legend-row { display: flex; align-items: center; gap: 6px; color: var(--color-text-secondary); }
.legend-val { margin-left: auto; color: #fff; font-weight: 600; }
</style>
