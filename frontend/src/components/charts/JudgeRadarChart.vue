<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { judgeRadarOption } from '@/utils/echartsTheme'

use([RadarChart, TooltipComponent, CanvasRenderer])

const props = defineProps<{ scores: { evidence: number; logic: number; compliance: number; operability: number; consistency: number } }>()

const option = computed(() => {
  const opt = JSON.parse(JSON.stringify(judgeRadarOption))
  opt.radar.indicator[0].name = `证据充分性\n(25%) ${props.scores.evidence}`
  opt.radar.indicator[1].name = `推理逻辑性\n(25%) ${props.scores.logic}`
  opt.radar.indicator[2].name = `安规合规性\n(20%) ${props.scores.compliance}`
  opt.radar.indicator[3].name = `可操作性\n(20%) ${props.scores.operability}`
  opt.radar.indicator[4].name = `历史一致性\n(10%) ${props.scores.consistency}`
  opt.series[0].data[0].value = [props.scores.evidence, props.scores.logic, props.scores.compliance, props.scores.operability, props.scores.consistency]
  return opt
})
</script>

<template>
  <v-chart :option="option" autoresize class="chart" />
</template>

<style scoped>.chart { width: 100%; height: 320px; }</style>
