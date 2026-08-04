<script setup lang="ts">
import { onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

let charts: echarts.ECharts[] = []

const colors = ['#00f0ff', '#00ff9d', '#ffcc00', '#b366ff']

function initCharts() {
  nextTick(() => {
    charts.forEach(c => c.dispose())
    charts = []

    const power = document.getElementById('chart-power')
    if (power) {
      const c = echarts.init(power)
      c.setOption({
        grid: { top: 10, right: 10, bottom: 20, left: 45 },
        xAxis: { type: 'category', data: Array.from({length:24},(_,i)=>`${i}:00`), axisLine:{lineStyle:{color:'#1a4a85'}}, axisLabel:{color:'#8ba0c8',fontSize:10} },
        yAxis: { type: 'value', splitLine:{show:false}, axisLabel:{color:'#8ba0c8'} },
        series: [{ data: Array.from({length:24},()=>Math.random()*250), type: 'bar', itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#00f0ff'},{offset:1,color:'rgba(0,240,255,0.1)'}])}, barWidth:'60%' }]
      })
      charts.push(c)
    }

    const trend = document.getElementById('chart-trend')
    if (trend) {
      const c = echarts.init(trend)
      c.setOption({
        legend: { data: ['今日','昨日'], textStyle:{color:'#8ba0c8'}, top:0, left:0, itemWidth:10, itemHeight:2 },
        grid: { top: 30, right: 10, bottom: 20, left: 45 },
        xAxis: { type: 'category', boundaryGap: false, data: ['00:00','04:00','08:00','12:00','16:00','20:00','24:00'], axisLine:{lineStyle:{color:'#1a4a85'}}, axisLabel:{color:'#8ba0c8'} },
        yAxis: { type: 'value', splitLine:{lineStyle:{color:'rgba(26,74,133,0.3)'}}, axisLabel:{color:'#8ba0c8'} },
        series: [
          { name: '今日', type: 'line', smooth: true, data: [800,1200,900,1500,2200,3456,3200], itemStyle:{color:'#00f0ff'}, areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,240,255,0.3)'},{offset:1,color:'rgba(0,240,255,0)'}])} },
          { name: '昨日', type: 'line', smooth: true, data: [600,900,1100,1300,1800,2100,2800], itemStyle:{color:'#00ff9d'}, lineStyle:{type:'dashed'} }
        ]
      })
      charts.push(c)
    }

    const status = document.getElementById('chart-status')
    if (status) {
      const c = echarts.init(status)
      c.setOption({
        series: [{ type: 'pie', radius: ['60%','80%'], label:{show:false}, data: [
          { value: 128, name: '运行中', itemStyle:{color:'#00f0ff'} },
          { value: 32, name: '维护中', itemStyle:{color:'#00ff9d'} },
          { value: 16, name: '故障', itemStyle:{color:'#ffcc00'} },
          { value: 24, name: '待机', itemStyle:{color:'#b366ff'} }
        ]}],
        graphic: { elements: [{ type: 'text', left: 'center', top: '40%', style:{text:'200',textAlign:'center',fill:'#fff',fontSize:18,fontWeight:'bold'} }] }
      })
      charts.push(c)
    }

    const dist = document.getElementById('chart-dist')
    if (dist) {
      const c = echarts.init(dist)
      c.setOption({
        series: [{ type: 'pie', radius: ['60%','80%'], label:{show:false}, data: [
          { value: 40, name: '场站A', itemStyle:{color:'#00f0ff'} },
          { value: 27, name: '场站B', itemStyle:{color:'#00ff9d'} },
          { value: 19, name: '场站C', itemStyle:{color:'#ffcc00'} },
          { value: 14, name: '场站D', itemStyle:{color:'#b366ff'} }
        ]}],
        graphic: { elements: [{ type: 'text', left: 'center', top: '40%', style:{text:'45,678\n总发电量',textAlign:'center',fill:'#fff',fontSize:13,fontWeight:'bold'} }] }
      })
      charts.push(c)
    }

    const week = document.getElementById('chart-week')
    if (week) {
      const c = echarts.init(week)
      c.setOption({
        grid: { top: 10, right: 10, bottom: 20, left: 50 },
        xAxis: { type: 'category', data: ['D1','D2','D3','D4','D5','D6','D7'], axisLine:{lineStyle:{color:'#1a4a85'}}, axisLabel:{color:'#8ba0c8'} },
        yAxis: { type: 'value', splitLine:{show:false}, axisLabel:{color:'#8ba0c8'} },
        series: [{ data: [32000,38000,42000,35000,31000,36000,45678], type: 'bar', itemStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#1a6aff'},{offset:1,color:'rgba(26,106,255,0.1)'}])}, barWidth:'50%' }]
      })
      charts.push(c)
    }
  })
}

onMounted(() => { initCharts(); window.addEventListener('resize', initCharts) })
onUnmounted(() => { charts.forEach(c => c.dispose()); window.removeEventListener('resize', initCharts) })
</script>

<template>
  <div class="dashboard-container">
    <div class="left-col">
      <div class="panel" style="flex:1">
        <div class="panel-title">实时发电功率 <span class="panel-unit">MW</span></div>
        <div style="font-size:28px;color:var(--color-accent);font-weight:bold;margin-bottom:5px">245.6</div>
        <div id="chart-power" class="chart-box"></div>
      </div>
      <div class="panel" style="flex:1">
        <div class="panel-title">发电量趋势 <span class="panel-unit">MWh</span></div>
        <div id="chart-trend" class="chart-box"></div>
      </div>
      <div class="panel" style="flex:1.2">
        <div class="panel-title">设备状态统计</div>
        <div style="display:flex;height:100%">
          <div id="chart-status" style="width:50%;height:100%"></div>
          <div style="width:50%;display:flex;flex-direction:column;justify-content:center;gap:10px;font-size:14px">
            <div><span style="color:#00f0ff">●</span> 运行中 <span style="float:right">128</span></div>
            <div><span style="color:#00ff9d">●</span> 维护中 <span style="float:right">32</span></div>
            <div><span style="color:#ffcc00">●</span> 故障停机 <span style="float:right">16</span></div>
            <div><span style="color:#b366ff">●</span> 待机 <span style="float:right">24</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="center-col">
      <div class="turbine-zone">
        <span class="turbine-icon">⚡</span>
        <div class="turbine-label">驭能 — 新能源场站智能诊断</div>
        <div class="floating-label" style="top:15%;right:15%"><div style="color:var(--color-text-secondary);font-size:11px">机组编号</div><div style="font-size:14px">INV-003</div></div>
        <div class="floating-label" style="top:40%;right:18%"><div style="color:var(--color-text-secondary);font-size:11px">运行状态</div><div style="font-size:14px;color:#00ff9d">正常运行</div></div>
        <div class="floating-label" style="top:65%;right:15%"><div style="color:var(--color-text-secondary);font-size:11px">实时功率</div><div style="font-size:14px">480 kW</div></div>

        <div class="bottom-cards">
          <div class="stat-card"><div class="lbl">设备总数</div><div class="val font-digital">200</div></div>
          <div class="stat-card"><div class="lbl">在线设备</div><div class="val font-digital" style="color:#00ff9d">185</div></div>
          <div class="stat-card"><div class="lbl">今日诊断</div><div class="val font-digital">12</div></div>
          <div class="stat-card"><div class="lbl">系统准确率</div><div class="val font-digital" style="color:#00f0ff">94.7%</div></div>
        </div>
      </div>
    </div>

    <div class="right-col">
      <div class="panel" style="flex:1">
        <div class="panel-title">发电量分布 <span class="panel-unit">MWh</span></div>
        <div style="display:flex;height:100%">
          <div id="chart-dist" style="width:50%;height:100%"></div>
          <div style="width:50%;display:flex;flex-direction:column;justify-content:center;gap:12px;font-size:13px">
            <div><span style="color:#00f0ff">●</span> 风电场A 18,456</div>
            <div><span style="color:#00ff9d">●</span> 风电场B 12,345</div>
            <div><span style="color:#ffcc00">●</span> 风电场C 8,765</div>
            <div><span style="color:#b366ff">●</span> 风电场D 6,112</div>
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
        <div class="panel-title">近7日发电量 <span class="panel-unit">MWh</span></div>
        <div id="chart-week" class="chart-box"></div>
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
.turbine-icon { font-size: 100px; opacity: 0.15; }
.turbine-label { margin-top: 16px; font-size: 20px; color: var(--color-accent); letter-spacing: 4px; }
.floating-label {
  position: absolute; background: rgba(0,20,50,0.9); border: 1px solid var(--color-accent);
  padding: 6px 14px; border-radius: 4px; pointer-events: none;
}
.bottom-cards { position: absolute; bottom: 10px; display: flex; gap: 16px; }
.stat-card .val { font-size: 22px; font-weight: bold; color: #fff; }
.stat-card .lbl { font-size: 12px; color: var(--color-text-secondary); }
.env-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; height: 100%; }
.env-item { background: rgba(255,255,255,0.04); border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 8px; }
.env-icon { font-size: 18px; margin-bottom: 4px; }
.env-lbl { font-size: 11px; color: var(--color-text-secondary); }
.env-val { font-size: 18px; font-weight: bold; }
</style>
