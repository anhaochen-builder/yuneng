import * as echarts from 'echarts'

const techBlueTheme = {
  color: ['#00f2f1', '#00c0ff', '#ffa022', '#ff4d4f', '#00e676', '#76ff03', '#ff6d00', '#d500f9'],
  backgroundColor: 'transparent',
  textStyle: { fontFamily: 'Share Tech Mono, Orbitron, monospace', color: '#e0e6ed' },
  title: { textStyle: { color: '#00f0ff', fontSize: 16, fontWeight: 'bold' }, subtextStyle: { color: '#8892a4', fontSize: 12 } },
  tooltip: { backgroundColor: 'rgba(10, 22, 40, 0.95)', borderColor: '#00f0ff', textStyle: { color: '#e0e6ed' } },
  legend: { textStyle: { color: '#8892a4' }, inactiveColor: '#334155' },
  grid: { left: '10%', right: '10%', top: '15%', bottom: '10%', containLabel: true },
  xAxis: { axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }, axisTick: { show: false }, axisLabel: { color: '#8892a4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' as any } } },
  yAxis: { axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }, axisTick: { show: false }, axisLabel: { color: '#8892a4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' as any } } },
}

echarts.registerTheme('techBlue', techBlueTheme)

export const scadaDualAxisOption = {
  tooltip: { trigger: 'axis' as const },
  legend: { data: ['有功功率(kW)', '电流(A)', '温度(°C)', '风速(m/s)'] },
  grid: { left: '10%', right: '15%', top: '15%', bottom: '15%', containLabel: true },
  xAxis: { type: 'category' as const, axisLabel: { color: '#8892a4' } },
  yAxis: [
    { type: 'value' as const, name: '功率/电流', axisLabel: { color: '#8892a4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
    { type: 'value' as const, name: '温度/风速', axisLabel: { color: '#8892a4' } },
  ],
  series: [
    { name: '有功功率(kW)', type: 'line', yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: '#00f2f1', width: 2 }, areaStyle: { color: { type: 'linear' as any, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,242,241,0.3)' }, { offset: 1, color: 'rgba(0,242,241,0)' }] } } },
    { name: '电流(A)', type: 'line', yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: '#00c0ff', width: 2 } },
    { name: '温度(°C)', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'none', lineStyle: { color: '#ffa022', width: 2 } },
    { name: '风速(m/s)', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'none', lineStyle: { color: '#00e676', width: 2 } },
  ],
}

export const judgeRadarOption = {
  tooltip: { backgroundColor: 'rgba(10,22,40,0.9)', borderColor: '#00f0ff' },
  radar: {
    indicator: [
      { name: '证据充分性\n(25%)', max: 100 },
      { name: '推理逻辑性\n(25%)', max: 100 },
      { name: '安规合规性\n(20%)', max: 100 },
      { name: '可操作性\n(20%)', max: 100 },
      { name: '历史一致性\n(10%)', max: 100 },
    ],
    shape: 'polygon' as any,
    radius: '65%',
    axisName: { color: '#8892a4', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(0,240,255,0.02)', 'rgba(0,240,255,0.05)'] } },
    splitLine: { lineStyle: { color: 'rgba(0,240,255,0.2)' } },
    axisLine: { lineStyle: { color: 'rgba(0,240,255,0.2)' } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [0, 0, 0, 0, 0],
      name: '评分',
      areaStyle: { color: 'rgba(0,242,241,0.2)' },
      lineStyle: { color: '#00f2f1', width: 2 },
      itemStyle: { color: '#00f2f1' },
    }],
  }],
}
