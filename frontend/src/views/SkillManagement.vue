<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { skillsApi, auditApi } from '@/api'

const skills = ref<any[]>([])
const agents = ref<any[]>([])
const auditData = ref<any>({})
const loading = ref(true)
const selectedSkill = ref<any>(null)

onMounted(async () => {
  try {
    const r = await skillsApi.list(); const d = r.data || r
    skills.value = d.skills || []
    agents.value = d.sub_agents || []
  } catch {}
  try { const r = await auditApi.skills(); auditData.value = r.data || r } catch {}
  loading.value = false
})
</script>

<template>
  <div class="skills-page animate-fade-in" v-loading="loading">
    <div class="top-stats">
      <div class="ts-item"><span class="ts-num font-digital data-glow" style="color:var(--color-accent)">{{ skills.length }}</span><span class="ts-lbl">Skills</span></div>
      <div class="ts-item"><span class="ts-num font-digital data-glow" style="color:#00d4aa">{{ agents.length }}</span><span class="ts-lbl">SubAgents</span></div>
      <div class="ts-item"><span class="ts-num font-digital data-glow" style="color:#7b68ee">{{ auditData.all_mapped ? '✓' : '✗' }}</span><span class="ts-lbl">映射完整</span></div>
    </div>

    <div class="main-grid">
      <div class="tech-card">
        <h4>🧠 技能列表</h4>
        <el-table :data="skills" size="small" highlight-current-row @row-click="(row:any) => selectedSkill = row">
          <el-table-column prop="skill_id" label="Skill ID" width="200" />
          <el-table-column prop="name" label="名称" />
          <el-table-column label="子智能体" width="180">
            <template #default="{ row: r }"><el-tag size="small" type="primary" effect="plain">{{ r.sub_agent || r.agent_id || '-' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default><el-tag size="small" type="success">active</el-tag></template>
          </el-table-column>
        </el-table>
      </div>

      <div class="tech-card">
        <h4>🤖 子智能体详情</h4>
        <div v-if="agents.length" class="agent-list">
          <div v-for="a in agents" :key="a.agent_id || a.name" class="agent-card" :class="{ selected: selectedSkill?.sub_agent === a.agent_id }">
            <div class="agent-header">
              <span class="agent-name">{{ a.name }}</span>
              <el-tag size="small" type="success">active</el-tag>
            </div>
            <div class="agent-id font-digital">{{ a.agent_id }}</div>
            <div class="agent-desc" v-if="a.description">{{ a.description }}</div>
            <div class="agent-triggers" v-if="a.intent_triggers">
              <el-tag v-for="t in a.intent_triggers" :key="t" size="small" effect="plain" class="trigger-tag">{{ t }}</el-tag>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">系统启动时自动注册子智能体</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.skills-page { display: flex; flex-direction: column; gap: 16px; }
.top-stats { display: flex; gap: 24px; }
.ts-item { display: flex; flex-direction: column; align-items: center; }
.ts-num { font-size: 28px; font-weight: 700; }
.ts-lbl { font-size: 12px; color: var(--color-text-secondary); }
.main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
h4 { color: var(--color-accent); margin-bottom: 14px; font-size: 14px; }
.agent-list { display: flex; flex-direction: column; gap: 10px; max-height: 500px; overflow-y: auto; }
.agent-card { padding: 14px; background: rgba(0,240,255,0.03); border-radius: 6px; border: 1px solid rgba(0,240,255,0.06); transition: border-color 0.2s;
  &.selected { border-color: var(--color-accent); }
}
.agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.agent-name { font-size: 14px; color: var(--color-text-primary); font-weight: 600; }
.agent-id { font-size: 11px; color: var(--color-accent); margin-bottom: 6px; }
.agent-desc { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; line-height: 1.5; }
.agent-triggers { display: flex; flex-wrap: wrap; gap: 4px; }
.trigger-tag { font-size: 10px; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 40px; }
</style>
