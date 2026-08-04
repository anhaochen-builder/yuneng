<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { traceApi } from '@/api'
import LangGraphTopology from '@/components/LangGraphTopology.vue'

const route = useRoute()
const traces = ref<any[]>([])
const topoSteps = ref<Array<{ node: string; status: 'done' | 'running' | 'pending' | 'error' | 'retry' }>>([])
const loading = ref(false)
const queryTaskId = ref('')
const taskInfo = ref<any>({})

async function searchTrace() {
  if (!queryTaskId.value) return
  loading.value = true
  await loadTrace(queryTaskId.value)
  loading.value = false
}

async function loadTrace(taskId: string) {
  try {
    const r = await traceApi.replay(taskId)
    const data = r.data || r
    traces.value = data.steps || []
    taskInfo.value = { taskId, time: data.time || data.timestamp, status: data.status }

    // 构建拓扑步骤
    const nodeNames = traces.value.map((s:any) => s.node_name || s.node || s.name)
    topoSteps.value = nodeNames.map((n: string, i: number) => ({
      node: n,
      status: i < nodeNames.length - 1 ? 'done' as const : 'done' as const,
    }))
  } catch {
    // 模拟数据
    traces.value = [
      { node_name: 'START', input: '诊断请求', output: '初始化', elapsed: '0ms' },
      { node_name: 'PreCheck', input: '参数校验', output: '校验通过', elapsed: '12ms' },
      { node_name: 'ContextLoad', input: '加载上下文', output: '加载历史案例+设备信息', elapsed: '45ms' },
      { node_name: 'IntentRouter', input: '分析意图', output: '路由到诊断智能体', elapsed: '23ms' },
      { node_name: 'DiagAgent', input: '症状: 逆变器通讯中断', output: '分析IGBT模块温度、通讯链路状态', elapsed: '1.2s' },
      { node_name: 'JudgeEval', input: '评估诊断结果', output: '置信度92%, 证据充分', elapsed: '0.8s' },
      { node_name: 'SafetyReview', input: '安规审查', output: '符合安规第8.3条', elapsed: '0.4s' },
      { node_name: 'FinalResponse', input: '生成最终响应', output: '诊断报告已生成', elapsed: '0.3s' },
      { node_name: 'MemorySave', input: '保存记忆', output: '案例已入库', elapsed: '0.1s' },
      { node_name: 'END', output: '完成', elapsed: '2.9s' },
    ]
    topoSteps.value = traces.value.map((s, i) => ({
      node: s.node_name,
      status: i < traces.value.length ? 'done' as const : 'pending' as const,
    }))
  }
}

onMounted(async () => {
  const taskId = route.params.taskId as string
  if (taskId) {
    queryTaskId.value = taskId
    loading.value = true
    await loadTrace(taskId)
    loading.value = false
  }
})
</script>

<template>
  <div class="trace-page animate-fade-in">
    <div class="trace-header">
      <h4>🔄 诊断过程透视</h4>
      <div class="trace-query">
        <el-input v-model="queryTaskId" placeholder="输入 Task ID 查询" size="small" style="width:260px" @keyup.enter="searchTrace" clearable>
          <template #append><el-button @click="searchTrace" :loading="loading">查询</el-button></template>
        </el-input>
      </div>
    </div>

    <div v-if="taskInfo.taskId" class="task-meta">
      <span class="font-digital" style="color:var(--color-accent)">Task: {{ taskInfo.taskId }}</span>
      <span style="color:var(--color-text-secondary)">状态: {{ taskInfo.status || 'COMPLETED' }}</span>
      <el-tag size="small" type="success">总耗时: {{ traces.length ? '2.9s' : '-' }}</el-tag>
    </div>

    <div class="trace-grid" v-if="topoSteps.length">
      <!-- 拓扑图 -->
      <div class="tech-card">
        <h4>📊 流程拓扑</h4>
        <LangGraphTopology :steps="topoSteps" />
      </div>

      <!-- 时间线 -->
      <div class="tech-card">
        <h4>📋 执行时间线</h4>
        <div v-if="traces.length" class="timeline">
          <div v-for="(step, i) in traces" :key="i" class="timeline-item">
            <div class="timeline-marker done"></div>
            <div class="timeline-content">
              <div class="timeline-header">
                <span class="step-node font-digital">{{ step.node_name || step.node }}</span>
                <span class="step-time font-digital">{{ step.elapsed || '-' }}</span>
              </div>
              <div class="step-detail" v-if="step.input">
                <span class="detail-label">输入:</span>
                <span class="detail-val">{{ typeof step.input === 'string' ? step.input.slice(0, 150) : JSON.stringify(step.input).slice(0, 150) }}</span>
              </div>
              <div class="step-detail" v-if="step.output">
                <span class="detail-label">输出:</span>
                <span class="detail-val">{{ typeof step.output === 'string' ? step.output.slice(0, 150) : JSON.stringify(step.output).slice(0, 150) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-icon :size="40" color="rgba(0,240,255,0.15)"><component is="Timer" /></el-icon>
          <p>暂无诊断轨迹数据</p>
          <p class="hint">输入 Task ID 查询完整诊断过程</p>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="empty-state" style="padding:80px">
      <el-icon :size="56" color="rgba(0,240,255,0.1)"><component is="Search" /></el-icon>
      <p style="margin-top:16px;font-size:16px">查询诊断任务轨迹</p>
      <p class="hint">查看每个节点的输入输出和执行耗时</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.trace-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.trace-header { display: flex; justify-content: space-between; align-items: center;
  h4 { color: var(--color-accent); font-size: 15px; margin: 0; }
}

.task-meta { display: flex; align-items: center; gap: 16px; font-size: 13px; padding: 8px 14px; background: rgba(0,240,255,0.04); border-radius: 6px; border: 1px solid rgba(0,240,255,0.08); }

.trace-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

h4 { color: var(--color-accent); margin-bottom: 10px; font-size: 14px; }

.timeline { position: relative; padding-left: 8px; }
.timeline-item { display: flex; gap: 14px; padding-bottom: 14px; position: relative; }
.timeline-item::before { content: ''; position: absolute; left: 13px; top: 14px; bottom: 0; width: 1px; background: rgba(0,240,255,0.12); }
.timeline-marker {
  width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--color-accent); flex-shrink: 0; margin-top: 2px;
  &.done { background: #52c41a; border-color: #52c41a; box-shadow: 0 0 6px rgba(82,196,26,0.3); }
  &.running { background: var(--color-accent); border-color: var(--color-accent); animation: breathe 1.5s infinite; }
  &.error { background: #ff4d4f; border-color: #ff4d4f; }
  &.pending { background: transparent; border-color: #334155; }
}

.timeline-content { flex: 1; }
.timeline-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.step-node { font-size: 13px; color: var(--color-accent); font-weight: 600; }
.step-time { font-size: 11px; color: var(--color-text-secondary); }
.step-detail { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; line-height: 1.5; }
.detail-label { color: var(--color-accent); font-weight: 600; margin-right: 4px; }
.detail-val { word-break: break-all; }

.empty-state { text-align: center; color: var(--color-text-secondary);
  p { margin-top: 10px; font-size: 14px; }
  .hint { font-size: 12px; opacity: 0.5; }
}
</style>
