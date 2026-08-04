import * as echarts from 'echarts'

const techBlueTheme = {
  color: ['#2FA7D1', '#40C9A0', '#F0A040', '#E85555', '#8B80F0', '#F0D060', '#E07040', '#60B8E0'],
  backgroundColor: 'transparent',
  textStyle: { fontFamily: 'Share Tech Mono, Orbitron, monospace', color: '#E8ECF1' },
  title: { textStyle: { color: '#2FA7D1', fontSize: 16, fontWeight: 'bold' }, subtextStyle: { color: '#8EA8C8', fontSize: 12 } },
  tooltip: { backgroundColor: 'rgba(4, 32, 79, 0.95)', borderColor: '#2FA7D1', textStyle: { color: '#E8ECF1' } },
  legend: { textStyle: { color: '#8EA8C8' }, inactiveColor: '#3A5070' },
  grid: { left: '10%', right: '10%', top: '15%', bottom: '10%', containLabel: true },
  xAxis: { axisLine: { lineStyle: { color: 'rgba(255,255,255,0.10)' } }, axisTick: { show: false }, axisLabel: { color: '#8EA8C8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' as any } } },
  yAxis: { axisLine: { lineStyle: { color: 'rgba(255,255,255,0.10)' } }, axisTick: { show: false }, axisLabel: { color: '#8EA8C8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' as any } } },
}

echarts.registerTheme('techBlue', techBlueTheme)

export const scadaDualAxisOption = {
  tooltip: { trigger: 'axis' as const },
  legend: { data: ['有功功率(kW)', '电流(A)', '温度(°C)', '风速(m/s)'] },
  grid: { left: '10%', right: '15%', top: '15%', bottom: '15%', containLabel: true },
  xAxis: { type: 'category' as const, axisLabel: { color: '#8EA8C8' } },
  yAxis: [
    { type: 'value' as const, name: '功率/电流', axisLabel: { color: '#8EA8C8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
    { type: 'value' as const, name: '温度/风速', axisLabel: { color: '#8EA8C8' } },
  ],
  series: [
    { name: '有功功率(kW)', type: 'line', yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: '#2FA7D1', width: 2 }, areaStyle: { color: { type: 'linear' as any, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(47,167,209,0.3)' }, { offset: 1, color: 'rgba(47,167,209,0)' }] } } },
    { name: '电流(A)', type: 'line', yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: '#40C9A0', width: 2 } },
    { name: '温度(°C)', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'none', lineStyle: { color: '#F0A040', width: 2 } },
    { name: '风速(m/s)', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'none', lineStyle: { color: '#8B80F0', width: 2 } },
  ],
}

export const judgeRadarOption = {
  tooltip: { backgroundColor: 'rgba(4,32,79,0.9)', borderColor: '#2FA7D1' },
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
    axisName: { color: '#8EA8C8', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(47,167,209,0.02)', 'rgba(47,167,209,0.06)'] } },
    splitLine: { lineStyle: { color: 'rgba(47,167,209,0.22)' } },
    axisLine: { lineStyle: { color: 'rgba(47,167,209,0.22)' } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [0, 0, 0, 0, 0],
      name: '评分',
      areaStyle: { color: 'rgba(47,167,209,0.22)' },
      lineStyle: { color: '#2FA7D1', width: 2 },
      itemStyle: { color: '#2FA7D1' },
    }],
  }],
}
