<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { scadaDualAxisOption } from '@/utils/echartsTheme'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  timeSeries: Array<{ time: string; power: number; current: number; temp: number; wind: number }>
  faultWindow?: { start: string; end: string }
}>()

const option = computed(() => {
  const opt = JSON.parse(JSON.stringify(scadaDualAxisOption))
  opt.xAxis.data = props.timeSeries.map(d => d.time)
  opt.series[0].data = props.timeSeries.map(d => d.power)
  opt.series[1].data = props.timeSeries.map(d => d.current)
  opt.series[2].data = props.timeSeries.map(d => d.temp)
  opt.series[3].data = props.timeSeries.map(d => d.wind)
  return opt
})
</script>

<template><v-chart :option="option" autoresize class="chart" /></template>
<style scoped>.chart { width: 100%; height: 320px; }</style>
