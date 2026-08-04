<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { scadaApi, toolsApi } from '@/api'

const devices = ref<any[]>([])
const selected = ref<any>(null)
const loading = ref(false)
const deviceData = ref<any>(null)
const querying = ref(false)

const mockDevices = [
  { device_id:'WT001', device_type:'wind_turbine', name:'1号风机', status:'running', temp:55, vibration:3.2, power:1500, location:'A区' },
  { device_id:'WT002', device_type:'wind_turbine', name:'2号风机', status:'running', temp:52, vibration:2.8, power:1480, location:'A区' },
  { device_id:'INV001', device_type:'inverter', name:'1号逆变器', status:'running', temp:62, vibration:1.5, power:480, location:'B区' },
  { device_id:'INV002', device_type:'inverter', name:'2号逆变器', status:'warning', temp:78, vibration:1.8, power:420, location:'B区' },
  { device_id:'TRA001', device_type:'transformer', name:'1号主变', status:'running', temp:68, vibration:0.8, power:3200, location:'C区' },
]

onMounted(async () => {
  loading.value = true
  try { const r = await scadaApi.devices(); devices.value = ((r.data||r) as any[])?.length ? (r.data||r) as any[] : mockDevices } catch { devices.value = mockDevices }
  loading.value = false
})

async function queryDevice(row: any) {
  selected.value = row
  querying.value = true
  try { const r = await scadaApi.data(row.device_id); deviceData.value = r.data || r } catch { deviceData.value = row }
  querying.value = false
}

function statusColor(s: string) { return s === 'running' ? 'success' : s === 'warning' ? 'warning' : s === 'fault' ? 'danger' : 'info' }
</script>

<template>
  <div class="device-page animate-fade-in">
    <div class="grid-2col">
      <div class="tech-card">
        <h4>📡 设备列表</h4>
        <el-table :data="devices" size="small" v-loading="loading" highlight-current-row @row-click="queryDevice">
          <el-table-column prop="device_id" label="设备ID" width="100" />
          <el-table-column prop="name" label="名称" width="100" />
          <el-table-column prop="device_type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row: r }"><el-tag size="small" :type="statusColor(r.status)">{{ r.status }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="temp" label="温度(°C)" width="90">
            <template #default="{ row: r }"><span :style="{color: (r.temp||0) > 70 ? '#ff4d4f' : (r.temp||0) > 55 ? '#ff9c40' : '#52c41a'}">{{ r.temp }}</span></template>
          </el-table-column>
          <el-table-column prop="power" label="功率(kW)" width="90" />
          <el-table-column prop="location" label="位置" />
        </el-table>
      </div>

      <div>
        <div class="tech-card" v-if="selected" v-loading="querying">
          <h4>🔍 {{ selected.name || selected.device_id }} 详情</h4>
          <div class="detail-grid">
            <div class="dg-item" v-for="(v,k) in (deviceData || selected)" :key="k">
              <span class="dgk">{{ k }}</span>
              <span class="dgv" :class="{ 'font-digital': typeof v === 'number' }">{{ typeof v === 'object' ? JSON.stringify(v).slice(0,60) : v }}</span>
            </div>
          </div>
        </div>

        <div class="tech-card" style="margin-top:16px">
          <h4>📊 统计概览</h4>
          <div class="summary-grid">
            <div class="sg-item"><div class="sgn font-digital" style="color:#52c41a">{{ devices.filter((d:any) => d.status === 'running').length }}</div><div class="sgl">运行中</div></div>
            <div class="sg-item"><div class="sgn font-digital" style="color:#ff9c40">{{ devices.filter((d:any) => d.status === 'warning').length }}</div><div class="sgl">告警</div></div>
            <div class="sg-item"><div class="sgn font-digital" style="color:#ff4d4f">{{ devices.filter((d:any) => d.status === 'fault').length }}</div><div class="sgl">故障</div></div>
            <div class="sg-item"><div class="sgn font-digital" style="color:var(--color-accent)">{{ devices.length }}</div><div class="sgl">总计</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.device-page { .grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } }
h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }
.detail-grid { display: flex; flex-direction: column; gap: 2px; max-height: 260px; overflow-y: auto; }
.dg-item { display: flex; gap: 12px; padding: 5px 0; border-bottom: 1px solid rgba(0,240,255,0.04); font-size: 12px; }
.dgk { color: var(--color-accent); min-width: 110px; }
.dgv { color: var(--color-text-secondary); word-break: break-all; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.sg-item { text-align: center; padding: 10px; background: rgba(0,240,255,0.03); border-radius: 6px; }
.sgn { font-size: 22px; font-weight: 700; }
.sgl { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }
</style>
