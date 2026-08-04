<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { feedbackApi, dashboardApi } from '@/api'

const stats = ref<any>({})
const recent = ref<any[]>([])

onMounted(async () => {
  try { const r = await feedbackApi.stats(); stats.value = (r.data || r) } catch {}
  try { const r = await dashboardApi.tasks('completed'); recent.value = ((r.data || r) as any)?.tasks?.slice(0, 10) || [] } catch {}
})
</script>

<template>
  <div class="feedback-page animate-fade-in">
    <div class="stats-row">
      <div class="stat-item tech-card">
        <div class="stat-val font-digital" style="color:#52c41a">{{ stats.total_accurate || 0 }}</div>
        <div class="stat-lbl">准确评价</div>
      </div>
      <div class="stat-item tech-card">
        <div class="stat-val font-digital" style="color:#ff9c40">{{ stats.total_partial || 0 }}</div>
        <div class="stat-lbl">部分准确</div>
      </div>
      <div class="stat-item tech-card">
        <div class="stat-val font-digital" style="color:#ff4d4f">{{ stats.total_inaccurate || 0 }}</div>
        <div class="stat-lbl">不准确</div>
      </div>
    </div>

    <div class="tech-card">
      <h4>📊 学习系统状态</h4>
      <div class="learning-grid">
        <div class="learn-card">
          <div class="learn-title">✅ 成功案例入库</div>
          <el-progress :percentage="Math.min(((stats.total_accurate || 0) / 50) * 100, 100)" :color="'#52c41a'" />
          <div class="learn-desc">{{ stats.total_accurate || 0 }}/50 触发 LoRA 微调</div>
        </div>
        <div class="learn-card">
          <div class="learn-title">🔧 Skill 自动生成</div>
          <el-progress :percentage="Math.min(((stats.total_accurate || 0) / 3) * 100, 100)" :color="'#00f0ff'" />
          <div class="learn-desc">≥3 例同模式自动提炼 Skill</div>
        </div>
        <div class="learn-card">
          <div class="learn-title">📝 待审核池</div>
          <div class="learn-val font-digital" style="color:#ff9c40">{{ stats.total_partial || 0 }}</div>
          <div class="learn-desc">部分准确案例待专家审核</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feedback-page { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-item { text-align: center; padding: 20px; }
.stat-val { font-size: 32px; font-weight: 700; }
.stat-lbl { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
h4 { color: var(--color-accent); margin-bottom: 16px; font-size: 13px; }
.learning-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.learn-card { text-align: center; }
.learn-title { font-size: 13px; color: var(--color-text-primary); margin-bottom: 10px; }
.learn-desc { font-size: 11px; color: var(--color-text-secondary); margin-top: 6px; }
.learn-val { font-size: 24px; }
</style>
