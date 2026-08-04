<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { traceApi } from '@/api'

const route = useRoute()
const traces = ref<any[]>([])
const loading = ref(false)
const queryTaskId = ref('')

async function searchTrace() {
  if (!queryTaskId.value) return
  loading.value = true
  try { const r = await traceApi.replay(queryTaskId.value); traces.value = (r.data || r).steps || [] } catch {}
  loading.value = false
}

onMounted(async () => {
  const taskId = route.params.taskId as string || 'demo'
  loading.value = true
  try { const r = await traceApi.replay(taskId); traces.value = (r.data || r).steps || [] } catch {}
  loading.value = false
})
</script>

<template>
  <div class="trace-page animate-fade-in">
    <div class="tech-card">
      <h4>🔄 诊断过程回放</h4>
      <p class="subtitle">任务ID: {{ route.params.taskId || 'demo' }}</p>

      <div v-if="traces.length" class="timeline">
        <div v-for="(step, i) in traces" :key="i" class="timeline-item">
          <div class="timeline-marker" :class="step.status || 'done'"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <span class="step-node font-digital">{{ step.node_name || step.node }}</span>
              <span class="step-time">{{ step.elapsed || '' }}</span>
            </div>
            <div class="step-detail" v-if="step.input">
              <span class="detail-label">输入:</span> {{ typeof step.input === 'string' ? step.input.slice(0, 200) : JSON.stringify(step.input).slice(0, 200) }}
            </div>
            <div class="step-detail" v-if="step.output">
              <span class="detail-label">输出:</span> {{ typeof step.output === 'string' ? step.output.slice(0, 200) : JSON.stringify(step.output).slice(0, 200) }}
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!loading" class="empty-state">
        <p>暂无诊断轨迹数据</p>
        <el-input v-model="queryTaskId" placeholder="输入 Task ID 查询" style="width:300px;margin-top:12px" @keyup.enter="searchTrace">
          <template #append><el-button @click="searchTrace">查询</el-button></template>
        </el-input>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trace-page { h4 { color: var(--color-accent); margin-bottom: 4px; } .subtitle { color: var(--color-text-secondary); font-size: 12px; margin-bottom: 16px; } }
.timeline { position: relative; padding-left: 20px; }
.timeline-item { display: flex; gap: 14px; padding-bottom: 16px; position: relative; }
.timeline-item::before { content: ''; position: absolute; left: 7px; top: 14px; bottom: 0; width: 1px; background: rgba(0,240,255,0.15); }
.timeline-marker { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--color-accent); flex-shrink: 0; margin-top: 2px;
  &.done { background: #52c41a; border-color: #52c41a; }
  &.running { background: var(--color-accent); animation: breathe 1.5s infinite; }
  &.error { background: var(--color-critical); border-color: var(--color-critical); }
}
.timeline-content { flex: 1; }
.timeline-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.step-node { font-size: 13px; color: var(--color-accent); }
.step-time { font-size: 11px; color: var(--color-text-secondary); }
.step-detail { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; line-height: 1.5; }
.detail-label { color: var(--color-accent); font-weight: 600; }
.empty-state { text-align: center; padding: 40px; color: var(--color-text-secondary); }
</style>
