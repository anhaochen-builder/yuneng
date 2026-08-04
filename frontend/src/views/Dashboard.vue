<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { dashboardApi, scadaApi, alarmApi } from '@/api'

let charts: echarts.ECharts[] = []
const stats = ref({ todayDiagnoses: 0, monthDiagnoses: 0, accuracy: 94.7, onlineDevices: 0 })
const alarmTypes = ref<Array<{ name: string; value: number; color: string }>>([])

onMounted(async () => {
  try { const r = await dashboardApi.overview(); Object.assign(stats.value, r.data || r) } catch {}
  try { const r = await scadaApi.devices(); stats.value.onlineDevices = Array.isArray(r.data) ? r.data.length : 5 } catch {}
  try {
    const r = await alarmApi.health()
    alarmTypes.value = [
      { name: '通讯中断', value: 45, color: '#00f0ff' },
      { name: '温度异常', value: 38, color: '#ffcc00' },
      { name: '振动超标', value: 22, color: '#ff4d4f' },
      { name: '绝缘降低', value: 15, color: '#b366ff' },
    ]
  } catch { alarmTypes.value = [{ name: '通讯中断', value: 45, color: '#00f0ff' },{ name: '温度异常', value: 38, color: '#ffcc00' },{ name: '振动超标', value: 22, color: '#ff4d4f' },{ name: '绝缘降低', value: 15, color: '#b366ff' }] }
  initCharts()
  window.addEventListener('resize', initCharts)
})

onUnmounted(() => { charts.forEach(c => c.dispose()); window.removeEventListener('resize', initCharts) })

function initCharts() {
  nextTick(() => {
    charts.forEach(c => c.dispose())
    charts = []

    // 1. 今日诊断次数 (柱状图)
    const el1 = document.getElementById('chart-diagnosis')
    if (el1) {
      const c = echarts.init(el1)
      c.setOption({
        grid: { top: 10, right: 10, bottom: 20, left: 40 },
        xAxis: { type: 'category', data: ['00:00','04:00','08:00','12:00','16:00','20:00','24:00'], axisLine:{lineStyle:{color:'#1a4a85'}}, axisLabel:{color:'#8ba0c8',fontSize:10} },
        yAxis: { type: 'value', splitLine:{show:false}, axisLabel:{color:'#8ba0c8'} },
        series: [{ data: [3,5,8,12,10,7,4], type: 'bar', itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#00f0ff'},{offset:1,color:'rgba(0,240,255,0.1)'}])}, barWidth:'50%' }]
      })
      charts.push(c)
    }

    // 2. Judge评分趋势 (折线图)
    const el2 = document.getElementById('chart-judge')
    if (el2) {
      const c = echarts.init(el2)
      c.setOption({
        legend: { data: ['评分','阈值'], textStyle:{color:'#8ba0c8'}, top:0, left:0, itemWidth:10, itemHeight:2 },
        grid: { top: 30, right: 10, bottom: 20, left: 40 },
        xAxis: { type: 'category', boundaryGap: false, data: ['00:00','04:00','08:00','12:00','16:00','20:00','24:00'], axisLine:{lineStyle:{color:'#1a4a85'}}, axisLabel:{color:'#8ba0c8'} },
        yAxis: { type: 'value', min: 0, max: 100, splitLine:{lineStyle:{color:'rgba(26,74,133,0.3)'}}, axisLabel:{color:'#8ba0c8'} },
        series: [
          { name: '评分', type: 'line', smooth: true, data: [82,78,85,72,88,92,87], itemStyle:{color:'#00f0ff'}, areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,240,255,0.3)'},{offset:1,color:'rgba(0,240,255,0)'}])}, markLine:{silent:true,data:[{yAxis:70,label:{formatter:'阈值70',color:'#ff4d4f'},lineStyle:{color:'#ff4d4f',type:'dashed'}}]} },
        ]
      })
      charts.push(c)
    }

    // 3. 设备状态分布 (环形图)
    const el3 = document.getElementById('chart-device')
    if (el3) {
      const c = echarts.init(el3)
      c.setOption({
        series: [{ type: 'pie', radius: ['60%','80%'], label:{show:false}, data: [
          { value: stats.value.onlineDevices || 5, name: '在线', itemStyle:{color:'#00ff9d'} },
          { value: 2, name: '告警', itemStyle:{color:'#ffcc00'} },
          { value: 1, name: '故障', itemStyle:{color:'#ff4d4f'} },
          { value: 1, name: '离线', itemStyle:{color:'#8ba0c8'} },
        ]}],
        graphic: { elements: [{ type: 'text', left: 'center', top: '40%', style:{text: `${(stats.value.onlineDevices||5)+4}\n总设备`,textAlign:'center',fill:'#fff',fontSize:14,fontWeight:'bold'} }] }
      })
      charts.push(c)
    }

    // 4. 告警类型分布 (环形图)
    const el4 = document.getElementById('chart-alarm-dist')
    if (el4) {
      const c = echarts.init(el4)
      c.setOption({
        series: [{ type: 'pie', radius: ['60%','80%'], label:{show:false}, data: alarmTypes.value.map(a => ({ ...a, itemStyle:{color:a.color} })) }],
        graphic: { elements: [{ type: 'text', left: 'center', top: '40%', style:{text:'120\n总告警',textAlign:'center',fill:'#fff',fontSize:13,fontWeight:'bold'} }] }
      })
      charts.push(c)
    }

    // 5. 近7日诊断趋势 (柱状图)
    const el5 = document.getElementById('chart-week-diag')
    if (el5) {
      const c = echarts.init(el5)
      c.setOption({
        grid: { top: 10, right: 10, bottom: 20, left: 45 },
        xAxis: { type: 'category', data: ['D1','D2','D3','D4','D5','D6','D7'], axisLine:{lineStyle:{color:'#1a4a85'}}, axisLabel:{color:'#8ba0c8'} },
        yAxis: { type: 'value', splitLine:{show:false}, axisLabel:{color:'#8ba0c8'} },
        series: [{ data: [8,12,9,15,11,14,Number(stats.value.todayDiagnoses)||12], type: 'bar', itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#1a6aff'},{offset:1,color:'rgba(26,106,255,0.1)'}])}, barWidth:'50%' }]
      })
      charts.push(c)
    }
  })
}
</script>

<template>
  <div class="dashboard-container">
    <!-- 左栏 -->
    <div class="left-col">
      <div class="panel" style="flex:1">
        <div class="panel-title">实时诊断次数 <span class="panel-unit">次</span></div>
        <div style="font-size:28px;color:var(--color-accent);font-weight:bold;margin-bottom:5px">{{ stats.todayDiagnoses || 12 }}</div>
        <div id="chart-diagnosis" class="chart-box"></div>
      </div>
      <div class="panel" style="flex:1">
        <div class="panel-title">Judge 评分趋势 <span class="panel-unit">分(阈值70)</span></div>
        <div id="chart-judge" class="chart-box"></div>
      </div>
      <div class="panel" style="flex:1.2">
        <div class="panel-title">设备状态统计</div>
        <div style="display:flex;height:100%">
          <div id="chart-device" style="width:50%;height:100%"></div>
          <div style="width:50%;display:flex;flex-direction:column;justify-content:center;gap:10px;font-size:14px">
            <div><span style="color:#00ff9d">●</span> 在线 <span style="float:right">{{ stats.onlineDevices || 5 }}</span></div>
            <div><span style="color:#ffcc00">●</span> 告警中 <span style="float:right">2</span></div>
            <div><span style="color:#ff4d4f">●</span> 故障停机 <span style="float:right">1</span></div>
            <div><span style="color:#8ba0c8">●</span> 离线 <span style="float:right">1</span></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 中栏 -->
    <div class="center-col">
      <div class="turbine-zone">
        <span class="turbine-icon">⚡</span>
        <div class="turbine-label">驭能智能诊断平台</div>
        <div class="turbine-sub">新能源场站非计划停机智能诊断</div>

        <div class="floating-label" style="top:12%;right:10%"><div style="color:var(--color-text-secondary);font-size:11px">子智能体</div><div style="font-size:14px">8 个就绪</div></div>
        <div class="floating-label" style="top:38%;right:14%"><div style="color:var(--color-text-secondary);font-size:11px">LLM 引擎</div><div style="font-size:14px;color:#00ff9d">DeepSeek V4</div></div>
        <div class="floating-label" style="top:65%;right:10%"><div style="color:var(--color-text-secondary);font-size:11px">知识库</div><div style="font-size:14px">160 条</div></div>

        <div class="bottom-cards">
          <div class="stat-card"><div class="lbl">今日诊断</div><div class="val font-digital">{{ stats.todayDiagnoses || 12 }}</div></div>
          <div class="stat-card"><div class="lbl">本月诊断</div><div class="val font-digital" style="color:#00ff9d">{{ stats.monthDiagnoses || 347 }}</div></div>
          <div class="stat-card"><div class="lbl">系统准确率</div><div class="val font-digital" style="color:#00f0ff">{{ stats.accuracy || 94.7 }}%</div></div>
          <div class="stat-card"><div class="lbl">Hook 拦截器</div><div class="val font-digital" style="color:#b366ff">12</div></div>
        </div>
      </div>
    </div>

    <!-- 右栏 -->
    <div class="right-col">
      <div class="panel" style="flex:1">
        <div class="panel-title">告警类型分布 <span class="panel-unit">本月</span></div>
        <div style="display:flex;height:100%">
          <div id="chart-alarm-dist" style="width:50%;height:100%"></div>
          <div style="width:50%;display:flex;flex-direction:column;justify-content:center;gap:10px;font-size:13px">
            <div v-for="a in alarmTypes" :key="a.name"><span :style="{color:a.color}">●</span> {{ a.name }} <span style="float:right">{{ a.value }}</span></div>
          </div>
        </div>
      </div>
      <div class="panel" style="flex:0.8">
        <div class="panel-title">环境监测</div>
        <div class="env-grid">
          <div class="env-item"><div class="env-icon">💨</div><div class="env-lbl">风速</div><div class="env-val font-digital">12.5<span style="font-size:12px">m/s</span></div></div>
          <div class="env-item"><div class="env-icon">🧭</div><div class="env-lbl">风向</div><div class="env-val">东南风</div></div>
          <div class="env-item"><div class="env-icon">🌡</div><div class="env-lbl">温度</div><div class="env-val font-digital">26.5<span style="font-size:12px">°C</span></div></div>
          <div class="env-item"><div class="env-icon">💧</div><div class="env-lbl">湿度</div><div class="env-val font-digital">62<span style="font-size:12px">%</span></div></div>
        </div>
      </div>
      <div class="panel" style="flex:1">
        <div class="panel-title">近7日诊断次数</div>
        <div id="chart-week-diag" class="chart-box"></div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dashboard-container {
  display: grid;
  grid-template-columns: 25% 50% 25%;
  height: 100%;
  gap: 16px;
  padding: 10px 20px;
}
.left-col, .right-col { display: flex; flex-direction: column; gap: 14px; }
.center-col { display: flex; justify-content: center; align-items: center; position: relative; }
.turbine-zone {
  width: 80%; height: 80%; display: flex; flex-direction: column; justify-content: center; align-items: center;
  background: radial-gradient(circle, rgba(0,100,255,0.08) 0%, transparent 70%); border-radius: 50%;
  position: relative;
}
.turbine-icon { font-size: 90px; opacity: 0.12; }
.turbine-label { margin-top: 12px; font-size: 22px; color: var(--color-accent); letter-spacing: 4px; font-weight: 700; }
.turbine-sub { font-size: 13px; color: var(--color-text-secondary); margin-top: 4px; }
.floating-label {
  position: absolute; background: rgba(0,20,50,0.9); border: 1px solid var(--color-accent);
  padding: 6px 14px; border-radius: 4px; pointer-events: none;
}
.bottom-cards { position: absolute; bottom: 10px; display: flex; gap: 16px; }
.stat-card .val { font-size: 20px; font-weight: bold; color: #fff; }
.stat-card .lbl { font-size: 11px; color: var(--color-text-secondary); }
.env-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; height: 100%; }
.env-item { background: rgba(255,255,255,0.04); border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 8px; }
.env-icon { font-size: 18px; margin-bottom: 4px; }
.env-lbl { font-size: 11px; color: var(--color-text-secondary); }
.env-val { font-size: 18px; font-weight: bold; }
</style>
