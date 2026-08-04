<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { skillsApi } from '@/api'

const skills = ref<any[]>([])
const agents = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const r = await skillsApi.list()
    const d = r.data || r
    skills.value = d.skills || []
    agents.value = d.sub_agents || []
  } catch {}
  loading.value = false
})
</script>

<template>
  <div class="skills-page animate-fade-in">
    <div class="grid-2col">
      <div class="tech-card">
        <h4>🧠 技能列表 ({{ skills.length }})</h4>
        <el-table :data="skills" size="small" v-loading="loading">
          <el-table-column prop="skill_id" label="技能ID" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="intent" label="触发意图" />
          <el-table-column prop="sub_agent" label="子智能体" />
        </el-table>
      </div>

      <div class="tech-card">
        <h4>🤖 子智能体 ({{ agents.length }})</h4>
        <div class="agent-list">
          <div v-for="a in agents" :key="a.agent_id || a" class="agent-item">
            <div class="agent-name">{{ a.name || a }}</div>
            <div class="agent-info" v-if="typeof a === 'object'">{{ a.description || a.intent_triggers?.join(', ') }}</div>
          </div>
        </div>
        <div v-if="!agents.length && !loading" class="empty-state">Skill 和子智能体在系统启动时自动注册</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skills-page { .grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } }
h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 13px; }
.agent-list { display: flex; flex-direction: column; gap: 8px; }
.agent-item { padding: 10px; background: rgba(0,240,255,0.04); border-radius: 6px; }
.agent-name { font-size: 13px; color: var(--color-accent); font-weight: 600; }
.agent-info { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 24px; }
</style>
