<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ data: Array<{ type: string; count: number }> }>()

const option = computed(() => ({
  tooltip: { trigger: 'item' as const, backgroundColor: 'rgba(10,22,40,0.9)', borderColor: '#00f0ff' },
  legend: { orient: 'vertical' as const, right: 5, top: 'center', textStyle: { color: '#8892a4', fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['45%', '70%'], center: ['40%', '50%'],
    data: props.data.map(d => ({ name: d.type, value: d.count })),
    label: { color: '#8892a4', fontSize: 10 },
    itemStyle: { borderColor: 'rgba(10,22,40,0.8)', borderWidth: 2 },
  }],
}))
</script>

<template>
  <v-chart :option="option" autoresize class="chart" />
</template>

<style scoped>.chart { width: 100%; height: 280px; }</style>
