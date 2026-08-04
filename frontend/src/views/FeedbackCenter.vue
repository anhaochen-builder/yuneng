<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { feedbackApi, dashboardApi } from '@/api'

const stats = ref({ total_accurate: 0, total_partial: 0, total_inaccurate: 0 })
const recentFeedback = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try { const r = await feedbackApi.stats(); Object.assign(stats.value, r.data || r) } catch {}
  try { const r = await dashboardApi.tasks('completed'); recentFeedback.value = ((r.data || r) as any)?.tasks?.slice(0, 8) || [] } catch {}
  loading.value = false
})

const totalEval = computed(() => (stats.value.total_accurate || 0) + (stats.value.total_partial || 0) + (stats.value.total_inaccurate || 0))
</script>

<template>
  <div class="feedback-page animate-fade-in" v-loading="loading">
    <div class="eval-stats">
      <div class="eval-card accurate"><div class="ec-num font-digital">{{ stats.total_accurate || 0 }}</div><div class="ec-label">准确评价</div></div>
      <div class="eval-card partial"><div class="ec-num font-digital">{{ stats.total_partial || 0 }}</div><div class="ec-label">部分准确</div></div>
      <div class="eval-card inaccurate"><div class="ec-num font-digital">{{ stats.total_inaccurate || 0 }}</div><div class="ec-label">不准确</div></div>
      <div class="eval-card total"><div class="ec-num font-digital">{{ totalEval }}</div><div class="ec-label">总计评价</div></div>
    </div>

    <div class="grid-2col">
      <div class="tech-card">
        <h4>📚 学习系统状态</h4>
        <div class="learn-cards">
          <div class="lc">
            <div class="lc-icon">✅</div>
            <div class="lc-title">成功案例入库</div>
            <el-progress :percentage="Math.min(((stats.total_accurate||0)/50)*100,100)" color="#52c41a" :stroke-width="8" />
            <div class="lc-hint">{{ stats.total_accurate || 0 }}/50 触发 LoRA 微调</div>
          </div>
          <div class="lc">
            <div class="lc-icon">🔧</div>
            <div class="lc-title">Skill 自动生成</div>
            <el-progress :percentage="Math.min(((stats.total_accurate||0)/3)*100,100)" color="#00f0ff" :stroke-width="8" />
            <div class="lc-hint">同模式 ≥3 例自动提炼</div>
          </div>
          <div class="lc">
            <div class="lc-icon">📝</div>
            <div class="lc-title">待审核池</div>
            <div class="lc-val font-digital" style="color:#ff9c40">{{ stats.total_partial || 0 }}</div>
            <div class="lc-hint">部分准确案例待审核</div>
          </div>
          <div class="lc">
            <div class="lc-icon">🎯</div>
            <div class="lc-title">负样本积累</div>
            <div class="lc-val font-digital" style="color:#ff4d4f">{{ stats.total_inaccurate || 0 }}</div>
            <div class="lc-hint">不准确案例已标记</div>
          </div>
        </div>
      </div>

      <div class="tech-card">
        <h4>🔄 学习闭环</h4>
        <div class="flow-diagram">
          <div class="flow-node start">诊断完成</div><div class="flow-arrow">→</div>
          <div class="flow-node">用户反馈</div><div class="flow-arrow">→</div>
          <div class="flow-branch">
            <div class="fb-item accurate">准确 → 向量化入库</div>
            <div class="fb-item partial">部分准确 → 待审核</div>
            <div class="fb-item inaccurate">不准确 → 负样本</div>
          </div>
        </div>
        <div class="triggers">
          <div class="trigger-item"><el-icon color="#52c41a"><component is="Check" /></el-icon> ≥3 例同模式 → Skill 自动生成</div>
          <div class="trigger-item"><el-icon color="#00f0ff"><component is="Check" /></el-icon> ≥50 例 → LoRA 增量微调</div>
          <div class="trigger-item"><el-icon color="#ff9c40"><component is="Check" /></el-icon> 时间衰减: 180 天半衰期</div>
        </div>
      </div>
    </div>

    <div class="tech-card" v-if="recentFeedback.length">
      <h4>📋 最近反馈记录</h4>
      <el-table :data="recentFeedback" size="small">
        <el-table-column prop="id" label="任务ID" width="180" />
        <el-table-column prop="name" label="任务名称" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row: r }"><el-tag size="small" type="success">{{ r.status || 'completed' }}</el-tag></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.feedback-page { display: flex; flex-direction: column; gap: 16px; }
.eval-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.eval-card { padding: 20px; text-align: center; border-radius: 6px; border: 1px solid; }
.eval-card.accurate { border-color: rgba(82,196,26,0.3); background: rgba(82,196,26,0.05); }
.eval-card.partial { border-color: rgba(255,156,64,0.3); background: rgba(255,156,64,0.05); }
.eval-card.inaccurate { border-color: rgba(255,77,79,0.3); background: rgba(255,77,79,0.05); }
.eval-card.total { border-color: rgba(0,240,255,0.2); background: rgba(0,240,255,0.05); }
.ec-num { font-size: 32px; font-weight: 700; color: var(--color-accent); }
.accurate .ec-num { color: #52c41a; }
.partial .ec-num { color: #ff9c40; }
.inaccurate .ec-num { color: #ff4d4f; }
.ec-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
h4 { color: var(--color-accent); margin-bottom: 14px; font-size: 14px; }
.learn-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.lc { text-align: center; padding: 12px; background: rgba(0,240,255,0.03); border-radius: 6px; }
.lc-icon { font-size: 24px; margin-bottom: 6px; }
.lc-title { font-size: 13px; color: var(--color-text-primary); margin-bottom: 8px; }
.lc-hint { font-size: 11px; color: var(--color-text-secondary); margin-top: 6px; }
.lc-val { font-size: 24px; font-weight: 700; }
.flow-diagram { display: flex; align-items: flex-start; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.flow-node { padding: 6px 14px; background: rgba(0,240,255,0.08); border-radius: 6px; font-size: 13px; color: var(--color-accent); border: 1px solid rgba(0,240,255,0.15); }
.flow-node.start { background: rgba(0,240,255,0.15); }
.flow-arrow { color: var(--color-text-secondary); font-size: 16px; line-height: 32px; }
.flow-branch { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.fb-item { font-size: 12px; padding: 4px 10px; border-radius: 4px; border-left: 3px solid; }
.fb-item.accurate { border-color: #52c41a; background: rgba(82,196,26,0.05); }
.fb-item.partial { border-color: #ff9c40; background: rgba(255,156,64,0.05); }
.fb-item.inaccurate { border-color: #ff4d4f; background: rgba(255,77,79,0.05); }
.triggers { display: flex; flex-direction: column; gap: 8px; }
.trigger-item { font-size: 12px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; }
</style>
