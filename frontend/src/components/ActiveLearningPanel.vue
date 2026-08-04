<script setup lang="ts">
import { ref } from 'vue'

const stats = ref({
  ingestedCases: 0,
  totalCases: 0,
  generatedSkills: 8,
  pendingReview: 0,
  totalAnnotated: 0,
})
</script>

<template>
  <div class="learning-panel tech-card">
    <h4>📚 主动学习系统</h4>
    <div class="learn-grid">
      <div class="learn-item">
        <div class="learn-title">✅ 成功案例入库</div>
        <el-progress :percentage="Math.min((stats.ingestedCases / 50) * 100, 100)" color="#52c41a" />
        <div class="learn-desc">{{ stats.ingestedCases }}/50 触发 LoRA 微调</div>
      </div>
      <div class="learn-item">
        <div class="learn-title">🔧 Skill 自动生成</div>
        <el-progress :percentage="Math.min((stats.generatedSkills / 15) * 100, 100)" color="#00f0ff" />
        <div class="learn-desc">{{ stats.generatedSkills }} 个 Skill 已生成 (阈值≥3次)</div>
      </div>
      <div class="learn-item">
        <div class="learn-title">📝 待审核池</div>
        <div class="learn-num font-digital" style="color:#ff9c40">{{ stats.pendingReview }}</div>
        <div class="learn-desc">部分准确案例待专家审核</div>
      </div>
      <div class="learn-item">
        <div class="learn-title">🎯 微调数据</div>
        <div class="learn-num font-digital" style="color:#7b68ee">{{ stats.totalAnnotated }}</div>
        <div class="learn-desc">累积标注案例数</div>
      </div>
    </div>

    <div class="learn-flow">
      <div class="flow-title">学习闭环流程</div>
      <div class="flow-steps">
        <span class="flow-step">诊断完成</span><span class="flow-arrow">→</span>
        <span class="flow-step">用户反馈</span><span class="flow-arrow">→</span>
        <span class="flow-step" :class="{ active: true }">准确→入库</span>
        <span class="flow-arrow">/</span>
        <span class="flow-step">不准确→负样本</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">≥3→Skill</span>
        <span class="flow-arrow">→</span>
        <span class="flow-step">≥50→LoRA</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.learning-panel { h4 { color: var(--color-accent); margin-bottom: 14px; font-size: 13px; } }
.learn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.learn-item { text-align: center; }
.learn-title { font-size: 13px; color: var(--color-text-primary); margin-bottom: 8px; }
.learn-desc { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }
.learn-num { font-size: 24px; font-weight: 700; }
.learn-flow { padding-top: 12px; border-top: 1px solid rgba(0,240,255,0.08); }
.flow-title { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 8px; }
.flow-steps { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; font-size: 11px; }
.flow-step { padding: 3px 8px; background: rgba(0,240,255,0.05); border-radius: 4px; color: var(--color-text-secondary); }
.flow-step.active { color: var(--color-accent); border: 1px solid var(--color-accent); }
.flow-arrow { color: var(--color-text-secondary); }
</style>
