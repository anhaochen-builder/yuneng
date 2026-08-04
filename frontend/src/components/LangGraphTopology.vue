<script setup lang="ts">
import { ref, computed } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

const props = defineProps<{ steps?: Array<{ node: string; status: 'done' | 'running' | 'pending' | 'error' | 'retry' }> }>()

const flowSteps = computed(() => props.steps?.length ? props.steps : [
  { node: 'START', status: 'done' },
  { node: 'PreCheck', status: 'done' },
  { node: 'ContextLoad', status: 'done' },
  { node: 'Router', status: 'done' },
  { node: 'Diagnosis并行', status: 'running' },
  { node: 'Judge评估', status: 'pending' },
  { node: 'SafetyReview', status: 'pending' },
  { node: 'FinalResponse', status: 'pending' },
  { node: 'MemorySave', status: 'pending' },
  { node: 'END', status: 'pending' },
])

const statusColors: Record<string, string> = { done: '#52c41a', running: '#00f0ff', pending: '#334155', error: '#ff4d4f', retry: '#ff9c40' }

const elements = computed(() => {
  const nodes: any[] = []
  const edges: any[] = []
  flowSteps.value.forEach((s, i) => {
    nodes.push({
      id: s.node, position: { x: i * 150, y: (i % 2) * 80 },
      data: { label: s.node },
      style: { background: statusColors[s.status] || '#334155', color: '#fff', border: `2px solid ${statusColors[s.status]}`, borderRadius: '8px', padding: '8px 14px', fontSize: '12px', fontFamily: 'Orbitron, monospace', width: 'auto' },
    })
    if (i > 0) {
      const prev = flowSteps.value[i - 1]
      if (prev) {
        edges.push({
          id: `${prev.node}-${s.node}`, source: prev.node, target: s.node,
          style: { stroke: s.status === 'retry' ? '#ff9c40' : s.status === 'error' ? '#ff4d4f' : '#00f0ff', strokeWidth: 1.5 },
          animated: s.status === 'running',
          markerEnd: { type: 'arrowclosed' as any, color: s.status === 'retry' ? '#ff9c40' : '#00f0ff' },
        })
      }
    }
  })
  return { nodes, edges }
})

const selectedNode = ref<any>(null)
function onNodeClick({ node }: any) { selectedNode.value = node }
</script>

<template>
  <div class="topology-container">
    <div class="flow-area">
      <VueFlow :nodes="elements.nodes" :edges="elements.edges" :default-viewport="{ zoom: 0.8 }" :min-zoom="0.2" :max-zoom="2" @node-click="onNodeClick" fit-view-on-init>
        <Background :gap="20" :size="1" color="rgba(0,240,255,0.05)" />
        <Controls position="bottom-right" />
      </VueFlow>
    </div>
    <div v-if="selectedNode" class="node-detail">
      <h4>{{ selectedNode.data?.label || selectedNode.id }}</h4>
      <p>状态: {{ selectedNode.style?.background }}</p>
    </div>
  </div>
</template>

<style scoped>
.topology-container { display: flex; flex-direction: column; height: 100%; }
.flow-area { flex: 1; min-height: 350px; background: rgba(10, 22, 40, 0.4); border-radius: 8px; border: 1px solid rgba(0, 240, 255, 0.1); overflow: hidden; }
.node-detail { padding: 10px 14px; border-top: 1px solid rgba(0, 240, 255, 0.1); font-size: 13px;
  h4 { color: var(--color-accent); margin-bottom: 4px; }
}
</style>
