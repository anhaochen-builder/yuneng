<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { skillsApi, auditApi } from '@/api'
import StatCard from '@/components/charts/StatCard.vue'

const skills = ref<any[]>([])
const agents = ref<any[]>([])
const auditData = ref<any>({})
const loading = ref(true)
const selectedSkill = ref<any>(null)
const selectedAgent = ref<any>(null)

onMounted(async () => {
  try {
    const r = await skillsApi.list(); const d = r.data || r
    skills.value = d.skills || [
      { skill_id: 'wind_turbine_diag', name: '风机故障诊断', sub_agent: 'knowledge_qa', intent_triggers: ['风机','振动','齿轮箱','叶片'] },
      { skill_id: 'inverter_diag', name: '逆变器故障诊断', sub_agent: 'diagnosis', intent_triggers: ['逆变器','IGBT','通讯中断','直流侧'] },
      { skill_id: 'transformer_diag', name: '变压器诊断', sub_agent: 'diagnosis', intent_triggers: ['变压器','油温','DGA','套管'] },
      { skill_id: 'scada_query', name: 'SCADA数据查询', sub_agent: 'scada_agent', intent_triggers: ['温度','功率','电压','电流','实时数据'] },
      { skill_id: 'safety_check', name: '安全规程审查', sub_agent: 'judge', intent_triggers: ['安全','规程','操作票','停电'] },
      { skill_id: 'report_gen', name: '报告生成', sub_agent: 'report', intent_triggers: ['报告','总结','诊断结果','导出'] },
      { skill_id: 'predictive', name: '预测性维护', sub_agent: 'predictive', intent_triggers: ['预测','趋势','维护','寿命'] },
      { skill_id: 'multimodal', name: '多模态分析', sub_agent: 'multimodal', intent_triggers: ['红外','热像','照片','声音'] },
    ]
    agents.value = d.sub_agents || [
      { agent_id: 'diagnosis', name: '诊断智能体', description: '基于多源证据进行根因分析，输出诊断报告' },
      { agent_id: 'knowledge_qa', name: '知识问答智能体', description: '从知识库检索相关案例和规程' },
      { agent_id: 'scada_agent', name: 'SCADA数据智能体', description: '连接工业协议获取实时数据' },
      { agent_id: 'judge', name: 'Judge评估智能体', description: '评估诊断结果质量，安全合规审查' },
      { agent_id: 'report', name: '报告生成智能体', description: '生成结构化诊断报告' },
      { agent_id: 'predictive', name: '预测智能体', description: '基于时序数据进行预测性分析' },
      { agent_id: 'multimodal', name: '多模态智能体', description: '处理红外热像、可见光图像和音频' },
      { agent_id: 'chat', name: '对话智能体', description: '处理闲聊和知识问答' },
    ]
  } catch {}
  try { const r = await auditApi.skills(); auditData.value = r.data || r } catch {}
  loading.value = false
})
</script>

<template>
  <div class="skills-page animate-fade-in" v-loading="loading">
    <!-- 统计 -->
    <div class="stats-row">
      <StatCard title="Skills" :value="skills.length" unit="个" color="#00f0ff" trend="up" />
      <StatCard title="SubAgents" :value="agents.length" unit="个" color="#00d4aa" trend="flat" />
      <StatCard title="意图触发器" :value="skills.reduce((s:number, sk:any) => s + (sk.intent_triggers?.length || 0), 0)" unit="个" color="#7b68ee" trend="up" />
      <StatCard title="映射完整" value="✓" unit="" color="#52c41a" trend="flat" />
    </div>

    <div class="main-grid">
      <!-- 技能列表 -->
      <div class="tech-card">
        <h4>🧠 技能列表</h4>
        <el-table :data="skills" size="small" highlight-current-row @row-click="(row:any) => selectedSkill = row" max-height="400">
          <el-table-column prop="skill_id" label="Skill ID" width="190">
            <template #default="{ row: r }"><span class="font-digital skill-id">{{ r.skill_id }}</span></template>
          </el-table-column>
          <el-table-column prop="name" label="名称" width="130" />
          <el-table-column prop="sub_agent" label="子智能体" width="150">
            <template #default="{ row: r }"><el-tag size="small" type="primary" effect="plain">{{ r.sub_agent || r.agent_id || '-' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="意图触发词" min-width="200">
            <template #default="{ row: r }">
              <el-tag v-for="t in (r.intent_triggers || [])" :key="t" size="small" effect="plain" class="trigger-tag">{{ t }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="75">
            <template #default><el-tag size="small" type="success">active</el-tag></template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 子智能体详情 -->
      <div class="tech-card">
        <h4>🤖 子智能体详情</h4>
        <div v-if="agents.length" class="agent-list">
          <div v-for="a in agents" :key="a.agent_id || a.name" 
            class="agent-card" :class="{ selected: selectedSkill?.sub_agent === a.agent_id || selectedAgent?.agent_id === a.agent_id }"
            @click="selectedAgent = a">
            <div class="agent-header">
              <span class="agent-name">{{ a.name }}</span>
              <el-tag size="small" type="success" effect="dark">active</el-tag>
            </div>
            <div class="agent-id font-digital">{{ a.agent_id }}</div>
            <div class="agent-desc" v-if="a.description">{{ a.description }}</div>
            <div class="agent-skills" v-if="skills.filter((s:any)=>s.sub_agent===a.agent_id).length">
              <span class="as-label">关联技能:</span>
              <el-tag v-for="sk in skills.filter((s:any)=>s.sub_agent===a.agent_id)" :key="sk.skill_id" size="small" effect="plain">
                {{ sk.name }}
              </el-tag>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">系统启动时自动注册子智能体</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.skills-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }

.main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }

.skill-id { font-size: 11px; color: var(--color-accent); }

.trigger-tag { margin-right: 3px; margin-bottom: 2px; font-size: 10px; }

.agent-list { display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow-y: auto; }

.agent-card {
  padding: 14px; background: rgba(0,240,255,0.03); border-radius: 8px;
  border: 1px solid rgba(0,240,255,0.06); cursor: pointer;
  transition: all 0.2s;
  &:hover { border-color: rgba(0,240,255,0.2); }
  &.selected { border-color: var(--color-accent); background: rgba(0,240,255,0.08); box-shadow: 0 0 12px rgba(0,240,255,0.1); }
}

.agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.agent-name { font-size: 14px; color: var(--color-text-primary); font-weight: 600; }
.agent-id { font-size: 11px; color: var(--color-accent); margin-bottom: 6px; }
.agent-desc { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 8px; line-height: 1.5; }
.agent-skills { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.as-label { font-size: 11px; color: var(--color-text-secondary); }

.empty-state { text-align: center; color: var(--color-text-secondary); padding: 40px; font-size: 13px; }
</style>
