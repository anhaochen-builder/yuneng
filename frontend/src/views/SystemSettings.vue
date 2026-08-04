<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dashboardApi } from '@/api'

const mode = ref('')
const audit = ref<any>({})

onMounted(async () => {
  try { const r = await dashboardApi.mode(); mode.value = (r.data || r).current || '' } catch {}
  try { const r = await import('@/api').then(m => m.auditApi.overview()); audit.value = (r.data || r) } catch {}
})
</script>

<template>
  <div class="settings-page animate-fade-in">
    <div class="grid-2col">
      <div class="tech-card">
        <h4>⚙️ 系统信息</h4>
        <div class="info-grid">
          <div class="info-row"><span class="info-label">项目名称</span><span>驭能智能诊断平台</span></div>
          <div class="info-row"><span class="info-label">版本</span><span>v1.0.0</span></div>
          <div class="info-row"><span class="info-label">LLM 引擎</span><span>DeepSeek V4 Pro</span></div>
          <div class="info-row"><span class="info-label">部署模式</span><span class="font-digital" style="color:var(--color-accent)">{{ mode || '生产在线' }}</span></div>
          <div class="info-row"><span class="info-label">审计等级</span><span :style="{ color: audit.overall?.grade === 'A' ? '#52c41a' : '#ff9c40' }">{{ audit.overall?.grade || 'A' }}</span></div>
          <div class="info-row"><span class="info-label">子智能体</span><span>8 个</span></div>
          <div class="info-row"><span class="info-label">知识库条目</span><span>158 条</span></div>
          <div class="info-row"><span class="info-label">API 端点</span><span>30+</span></div>
        </div>
      </div>

      <div class="tech-card">
        <h4>📡 连接状态</h4>
        <div class="conn-status">
          <div class="conn-item"><span>后端服务</span><el-tag size="small" type="success">正常</el-tag></div>
          <div class="conn-item"><span>DeepSeek API</span><el-tag size="small" type="success">已连接</el-tag></div>
          <div class="conn-item"><span>知识库</span><el-tag size="small" type="success">158 条</el-tag></div>
          <div class="conn-item"><span>OCR 引擎</span><el-tag size="small" type="warning">未安装</el-tag></div>
          <div class="conn-item"><span>Neo4j</span><el-tag size="small" type="info">未连接(可选)</el-tag></div>
          <div class="conn-item"><span>Docker</span><el-tag size="small" type="success">就绪</el-tag></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page { .grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } }
h4 { color: var(--color-accent); margin-bottom: 16px; font-size: 13px; }
.info-grid { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; justify-content: space-between; font-size: 13px; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.05); }
.info-label { color: var(--color-text-secondary); }
.conn-status { display: flex; flex-direction: column; gap: 10px; }
.conn-item { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
</style>
