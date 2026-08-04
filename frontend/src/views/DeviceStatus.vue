<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { scadaApi, toolsApi } from '@/api'

const devices = ref<any[]>([])
const selected = ref<any>(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try { const r = await scadaApi.devices(); devices.value = Array.isArray(r.data) ? r.data : (r.data || r) as any[] } catch {}
  loading.value = false
})

async function queryDevice(deviceId: string) {
  try { const r = await toolsApi.list(); } catch {}
  try { const r = await scadaApi.data(deviceId); selected.value = r.data || r } catch {}
}
</script>

<template>
  <div class="device-page animate-fade-in">
    <div class="grid-2col">
      <div class="tech-card">
        <h4>📡 设备列表</h4>
        <el-table :data="devices" size="small" v-loading="loading" @row-click="(row: any) => queryDevice(row.device_id || row)">
          <el-table-column prop="device_id" label="设备ID" />
          <el-table-column prop="device_type" label="类型" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row: r }"><el-tag size="small" :type="r.status === 'running' ? 'success' : 'warning'">{{ r.status || '运行中' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row: r }"><el-button size="small" text type="primary" @click.stop="queryDevice(r.device_id || r)">查看</el-button></template>
          </el-table-column>
        </el-table>
        <div v-if="!devices.length && !loading" class="empty-state">暂无设备，请先在 SCADA 看板连接设备</div>
      </div>

      <div class="tech-card" v-if="selected">
        <h4>🔍 设备详情</h4>
        <div class="detail-grid">
          <div v-for="(v, k) in selected" :key="k" class="detail-row">
            <span class="detail-key">{{ k }}</span>
            <span class="detail-val">{{ typeof v === 'object' ? JSON.stringify(v).slice(0, 100) : v }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.device-page { .grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } }
h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 13px; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 24px; }
.detail-grid { display: flex; flex-direction: column; gap: 4px; max-height: 500px; overflow-y: auto; }
.detail-row { display: flex; gap: 12px; padding: 4px 0; border-bottom: 1px solid rgba(0,240,255,0.05); font-size: 12px; }
.detail-key { color: var(--color-accent); min-width: 120px; }
.detail-val { color: var(--color-text-secondary); word-break: break-all; }
</style>
