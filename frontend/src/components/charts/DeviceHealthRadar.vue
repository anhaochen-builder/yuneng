<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([RadarChart, TooltipComponent, CanvasRenderer])

const props = defineProps<{ scores: { rpm: number; temp: number; vibration: number; voltage: number; oilTemp: number } }>()

const option = computed(() => ({
  tooltip: { backgroundColor: 'rgba(10,22,40,0.9)', borderColor: '#00f0ff' },
  radar: {
    indicator: [
      { name: '转速', max: 100 }, { name: '温度', max: 100 },
      { name: '振动', max: 100 }, { name: '电压', max: 100 }, { name: '油温', max: 100 },
    ],
    shape: 'polygon' as any, radius: '65%',
    axisName: { color: '#8892a4', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(0,240,255,0.02)', 'rgba(0,240,255,0.05)'] } },
    splitLine: { lineStyle: { color: 'rgba(0,240,255,0.2)' } },
    axisLine: { lineStyle: { color: 'rgba(0,240,255,0.2)' } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [props.scores.rpm, props.scores.temp, props.scores.vibration, props.scores.voltage, props.scores.oilTemp],
      name: '健康度', areaStyle: { color: 'rgba(0,242,241,0.2)' },
      lineStyle: { color: '#00f2f1', width: 2 }, itemStyle: { color: '#00f2f1' },
    }],
  }],
}))
</script>

<template><v-chart :option="option" autoresize class="chart" /></template>
<style scoped>.chart { width: 100%; height: 300px; }</style>
