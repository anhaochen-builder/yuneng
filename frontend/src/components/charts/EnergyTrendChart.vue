<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ predicted: number[]; actual: number[]; labels: string[] }>()

const option = computed(() => ({
  tooltip: { trigger: 'axis' as const, backgroundColor: 'rgba(10,22,40,0.9)', borderColor: '#00f0ff' },
  legend: { data: ['预测', '实际'], textStyle: { color: '#8892a4' }, top: 0 },
  grid: { left: '8%', right: '5%', top: '15%', bottom: '8%' },
  xAxis: { type: 'category' as const, data: props.labels, axisLabel: { color: '#8892a4', fontSize: 10 } },
  yAxis: { type: 'value' as const, name: 'kWh', axisLabel: { color: '#8892a4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
  series: [
    { name: '预测', type: 'line', data: props.predicted, smooth: true, symbol: 'none', lineStyle: { color: '#7b68ee', type: 'dashed', width: 2 } },
    { name: '实际', type: 'line', data: props.actual, smooth: true, symbol: 'none', lineStyle: { color: '#00f0ff', width: 2 }, areaStyle: { color: { type: 'linear' as any, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,240,255,0.2)' }, { offset: 1, color: 'rgba(0,240,255,0)' }] } } },
  ],
}))
</script>

<template>
  <v-chart :option="option" autoresize class="chart" />
</template>

<style scoped>.chart { width: 100%; height: 280px; }</style>
