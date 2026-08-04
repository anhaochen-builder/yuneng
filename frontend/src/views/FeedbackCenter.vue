<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { feedbackApi, dashboardApi } from '@/api'
import ActiveLearningPanel from '@/components/ActiveLearningPanel.vue'

const stats = ref({ total_accurate: 0, total_partial: 0, total_inaccurate: 0 })
const recentFeedback = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try { const r = await feedbackApi.stats(); Object.assign(stats.value, r.data || r) } catch {}
  try { const r = await dashboardApi.tasks('completed'); recentFeedback.value = ((r.data || r) as any)?.tasks?.slice(0, 10) || [] } catch {}
  loading.value = false
})

const totalEval = computed(() => (stats.value.total_accurate || 0) + (stats.value.total_partial || 0) + (stats.value.total_inaccurate || 0))
const accuracyRate = computed(() => totalEval.value > 0 ? Math.round((stats.value.total_accurate || 0) / totalEval.value * 100) : 0)

const feedbackTimeline = ref([
  { time: '10:32', user: '张工', task: 'DX-20260804-001', result: '准确', comment: '诊断结果准确，有效避免了误拆检' },
  { time: '09:15', user: '李工', task: 'DX-20260804-002', result: '部分准确', comment: '根因分析正确，但处置建议不够详细' },
  { time: '昨天 16:40', user: '王工', task: 'DX-20260803-008', result: '准确', comment: '变压器诊断结果完全正确' },
  { time: '昨天 14:20', user: '赵工', task: 'DX-20260803-006', result: '不准确', comment: '误判为机械故障，实际是电气连接问题' },
  { time: '昨天 11:05', user: '孙工', task: 'DX-20260803-005', result: '准确', comment: '从告警到给出处置方案不到3分钟' },
])
</script>

<template>
  <div class="feedback-page animate-fade-in" v-loading="loading">
    <!-- 评价统计 -->
    <div class="eval-stats">
      <div class="eval-card accurate">
        <div class="ec-icon">✅</div>
        <div class="ec-num font-digital">{{ stats.total_accurate || 0 }}</div>
        <div class="ec-label">准确评价</div>
      </div>
      <div class="eval-card partial">
        <div class="ec-icon">🤔</div>
        <div class="ec-num font-digital">{{ stats.total_partial || 0 }}</div>
        <div class="ec-label">部分准确</div>
      </div>
      <div class="eval-card inaccurate">
        <div class="ec-icon">❌</div>
        <div class="ec-num font-digital">{{ stats.total_inaccurate || 0 }}</div>
        <div class="ec-label">不准确</div>
      </div>
      <div class="eval-card total">
        <div class="ec-icon">📊</div>
        <div class="ec-num font-digital">{{ totalEval }}</div>
        <div class="ec-label">总计评价</div>
      </div>
      <div class="eval-card rate">
        <div class="ec-icon">🎯</div>
        <div class="ec-num font-digital" :style="{color: accuracyRate >= 80 ? '#52c41a' : accuracyRate >= 60 ? '#ff9c40' : '#ff4d4f'}">{{ accuracyRate }}%</div>
        <div class="ec-label">准确率</div>
      </div>
    </div>

    <div class="grid-2col">
      <!-- 主动学习面板 -->
      <ActiveLearningPanel />

      <!-- 学习闭环 -->
      <div class="tech-card">
        <h4>🔄 学习闭环流程</h4>
        <div class="flow-diagram">
          <div class="flow-row">
            <div class="flow-node start">诊断完成</div>
            <span class="flow-arrow">→</span>
            <div class="flow-node">用户反馈</div>
            <span class="flow-arrow">→</span>
            <div class="flow-node">评价分类</div>
          </div>
          <div class="flow-branches">
            <div class="fb-item accurate">
              <span class="fb-icon">✅</span>
              <div>
                <div class="fb-title">准确案例 → 向量化入库</div>
                <div class="fb-desc">自动提取诊断模式，存入成功案例库</div>
              </div>
            </div>
            <div class="fb-item partial">
              <span class="fb-icon">🤔</span>
              <div>
                <div class="fb-title">部分准确 → 专家审核</div>
                <div class="fb-desc">人工修正根因后补充入库</div>
              </div>
            </div>
            <div class="fb-item inaccurate">
              <span class="fb-icon">❌</span>
              <div>
                <div class="fb-title">不准确 → 负样本积累</div>
                <div class="fb-desc">标记为负例，用于后续对比学习</div>
              </div>
            </div>
          </div>
        </div>

        <div class="triggers">
          <div class="trigger-title">自动触发条件</div>
          <div class="trigger-item"><el-icon color="#52c41a"><component is="Check" /></el-icon> 同模式 ≥3 例 → Skill 自动生成</div>
          <div class="trigger-item"><el-icon color="#00f0ff"><component is="Check" /></el-icon> 累计 ≥50 例成功案例 → LoRA 增量微调</div>
          <div class="trigger-item"><el-icon color="#ff9c40"><component is="Check" /></el-icon> 时间衰减机制: 180 天半衰期</div>
          <div class="trigger-item"><el-icon color="#7b68ee"><component is="Check" /></el-icon> 置信度 <0.4 的案例自动入待审核池</div>
        </div>
      </div>
    </div>

    <!-- 反馈时间线 -->
    <div class="tech-card" v-if="feedbackTimeline.length">
      <h4>📋 最近反馈记录</h4>
      <div class="feedback-timeline">
        <div v-for="(fb, i) in feedbackTimeline" :key="i" class="ft-item">
          <div class="ft-time">{{ fb.time }}</div>
          <div class="ft-content">
            <div class="ft-header">
              <span class="ft-user">{{ fb.user }}</span>
              <span class="ft-task font-digital">{{ fb.task }}</span>
              <el-tag size="small" :type="fb.result === '准确' ? 'success' : fb.result === '部分准确' ? 'warning' : 'danger'">
                {{ fb.result }}
              </el-tag>
            </div>
            <div class="ft-comment" v-if="fb.comment">{{ fb.comment }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.feedback-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.eval-stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.eval-card {
  padding: 18px; text-align: center; border-radius: 8px; border: 1px solid;
  transition: transform 0.2s;
  &:hover { transform: translateY(-2px); }
}
.eval-card.accurate { border-color: rgba(82,196,26,0.3); background: rgba(82,196,26,0.06); }
.eval-card.partial { border-color: rgba(255,156,64,0.3); background: rgba(255,156,64,0.06); }
.eval-card.inaccurate { border-color: rgba(255,77,79,0.3); background: rgba(255,77,79,0.06); }
.eval-card.total { border-color: rgba(0,240,255,0.2); background: rgba(0,240,255,0.04); }
.eval-card.rate { border-color: rgba(123,104,238,0.3); background: rgba(123,104,238,0.06); }

.ec-icon { font-size: 24px; margin-bottom: 4px; }
.ec-num { font-size: 30px; font-weight: 700; }
.accurate .ec-num { color: #52c41a; }
.partial .ec-num { color: #ff9c40; }
.inaccurate .ec-num { color: #ff4d4f; }
.total .ec-num, .rate .ec-num { color: var(--color-accent); }
.ec-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }

.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }

.flow-diagram { margin-bottom: 14px; }
.flow-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.flow-node { padding: 6px 14px; background: rgba(0,240,255,0.08); border-radius: 6px; font-size: 13px; color: var(--color-accent); border: 1px solid rgba(0,240,255,0.15); }
.flow-node.start { background: rgba(0,240,255,0.15); }
.flow-arrow { color: var(--color-text-secondary); font-size: 16px; }

.flow-branches { display: flex; flex-direction: column; gap: 8px; }
.fb-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border-radius: 6px; border-left: 3px solid; }
.fb-item.accurate { border-color: #52c41a; background: rgba(82,196,26,0.05); }
.fb-item.partial { border-color: #ff9c40; background: rgba(255,156,64,0.05); }
.fb-item.inaccurate { border-color: #ff4d4f; background: rgba(255,77,79,0.05); }
.fb-icon { font-size: 18px; flex-shrink: 0; }
.fb-title { font-size: 13px; color: var(--color-text-primary); font-weight: 600; }
.fb-desc { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }

.triggers {
  padding-top: 12px; border-top: 1px solid rgba(0,240,255,0.08);
  .trigger-title { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 8px; font-weight: 600; }
}
.trigger-item { font-size: 12px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 8px; padding: 4px 0; }

.feedback-timeline { display: flex; flex-direction: column; gap: 0; }
.ft-item { display: flex; gap: 14px; padding: 10px 0; border-bottom: 1px solid rgba(0,240,255,0.05); }
.ft-time { font-size: 11px; color: var(--color-text-secondary); min-width: 60px; padding-top: 2px; }
.ft-content { flex: 1; }
.ft-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.ft-user { font-size: 13px; color: var(--color-text-primary); font-weight: 500; }
.ft-task { font-size: 11px; color: var(--color-accent); }
.ft-comment { font-size: 12px; color: var(--color-text-secondary); line-height: 1.5; }
</style>
