<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  shortTerm?: Array<{ question: string; answer: string; time: string }>
  workMemory?: Record<string, any>
  longTerm?: { totalCases: number; recentCases: Array<{ deviceType: string; faultType: string; time: string; confidence: number }> }
}>()

const activeTab = ref('short')
</script>

<template>
  <div class="memory-panel tech-card">
    <h4>🧠 三层记忆系统</h4>
    <div class="tabs">
      <span class="tab" :class="{ active: activeTab === 'short' }" @click="activeTab = 'short'">短期记忆</span>
      <span class="tab" :class="{ active: activeTab === 'work' }" @click="activeTab = 'work'">工作记忆</span>
      <span class="tab" :class="{ active: activeTab === 'long' }" @click="activeTab = 'long'">长期记忆</span>
    </div>

    <div v-if="activeTab === 'short'" class="tab-content">
      <div v-for="(s, i) in (shortTerm || [])" :key="i" class="memory-item">
        <div class="mem-q"><span class="role-tag user">用户</span>{{ s.question?.slice(0, 80) }}</div>
        <div class="mem-a"><span class="role-tag ai">AI</span>{{ s.answer?.slice(0, 80) }}</div>
        <div class="mem-time">{{ s.time }}</div>
      </div>
      <div v-if="!shortTerm?.length" class="empty">暂无短期记忆</div>
    </div>

    <div v-if="activeTab === 'work'" class="tab-content">
      <div class="work-groups">
        <div class="work-group"><div class="wg-title">输入层</div><div class="wg-items">{{ Object.entries(workMemory || {}).filter(([k]) => ['input', 'cleaned_input', 'rewritten_query'].includes(k)).map(([k,v]) => `${k}: ${String(v).slice(0, 30)}`).join(' | ') || '空' }}</div></div>
        <div class="work-group"><div class="wg-title">意图层</div><div class="wg-items">{{ Object.entries(workMemory || {}).filter(([k]) => ['intent', 'confidence', 'entities'].includes(k)).map(([k,v]) => `${k}: ${JSON.stringify(v).slice(0, 40)}`).join(' | ') || '空' }}</div></div>
        <div class="work-group"><div class="wg-title">质量层</div><div class="wg-items">{{ Object.entries(workMemory || {}).filter(([k]) => ['judge_score', 'retry_count'].includes(k)).map(([k,v]) => `${k}: ${v}`).join(' | ') || '空' }}</div></div>
      </div>
      <div v-if="!workMemory || !Object.keys(workMemory).length" class="empty">暂无工作记忆</div>
    </div>

    <div v-if="activeTab === 'long'" class="tab-content">
      <div class="lt-stats">
        <div class="lt-stat"><span class="lt-num font-digital">{{ longTerm?.totalCases || 0 }}</span>入库案例</div>
        <div class="lt-stat"><span class="lt-num font-digital">180天</span>半衰期</div>
      </div>
      <div v-for="(c, i) in (longTerm?.recentCases || []).slice(0, 5)" :key="i" class="lt-case">
        <span>{{ c.deviceType }} / {{ c.faultType }}</span>
        <span class="lt-conf">{{ ((c.confidence || 0) * 100).toFixed(0) }}%</span>
      </div>
      <div v-if="!longTerm?.recentCases?.length" class="empty">暂无长期记忆案例</div>
    </div>
  </div>
</template>

<style scoped>
.memory-panel { h4 { color: var(--color-accent); margin-bottom: 10px; font-size: 13px; } }
.tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.tab { padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; color: var(--color-text-secondary); border: 1px solid transparent; }
.tab.active { color: var(--color-accent); border-color: var(--color-accent); background: var(--color-accent-dim); }
.tab-content { font-size: 12px; }
.memory-item { padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.05); }
.mem-q, .mem-a { line-height: 1.5; }
.mem-time { font-size: 10px; color: var(--color-text-secondary); margin-top: 2px; }
.role-tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; margin-right: 6px; }
.role-tag.user { background: rgba(0,102,255,0.3); color: #00c0ff; }
.role-tag.ai { background: rgba(0,240,255,0.15); color: var(--color-accent); }
.work-groups { display: flex; flex-direction: column; gap: 8px; }
.work-group { padding: 6px 8px; background: rgba(0,240,255,0.03); border-radius: 4px; }
.wg-title { color: var(--color-accent); font-weight: 600; margin-bottom: 2px; }
.wg-items { color: var(--color-text-secondary); word-break: break-all; }
.lt-stats { display: flex; gap: 16px; margin-bottom: 10px; }
.lt-stat { font-size: 12px; color: var(--color-text-secondary); }
.lt-num { font-size: 20px; color: var(--color-accent); display: block; }
.lt-case { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid rgba(0,240,255,0.05); }
.lt-conf { color: var(--color-accent); }
.empty { text-align: center; color: var(--color-text-secondary); padding: 16px; }
</style>
