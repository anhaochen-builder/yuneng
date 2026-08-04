<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ data: Array<{ hour: string; power: number }> }>()

const option = computed(() => ({
  tooltip: { trigger: 'axis' as const, backgroundColor: 'rgba(10,22,40,0.9)', borderColor: '#00f0ff' },
  grid: { left: '8%', right: '5%', top: '10%', bottom: '8%' },
  xAxis: { type: 'category' as const, data: props.data.map(d => d.hour), axisLabel: { color: '#8892a4', fontSize: 10 } },
  yAxis: { type: 'value' as const, name: 'kW', axisLabel: { color: '#8892a4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
  series: [{
    type: 'bar', data: props.data.map(d => d.power),
    itemStyle: { color: { type: 'linear' as any, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#00f0ff' }, { offset: 1, color: '#00d4aa' }] }, borderRadius: [4, 4, 0, 0] },
    barWidth: '60%',
  }],
}))
</script>

<template>
  <v-chart :option="option" autoresize class="chart" />
</template>

<style scoped>.chart { width: 100%; height: 280px; }</style>
