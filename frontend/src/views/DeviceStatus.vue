<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { scadaApi, toolsApi } from '@/api'
import StatCard from '@/components/charts/StatCard.vue'

const devices = ref<any[]>([])
const selected = ref<any>(null)
const loading = ref(false)
const deviceData = ref<any>(null)
const querying = ref(false)
const searchText = ref('')
const showAddDialog = ref(false)
const adding = ref(false)
const newDevice = ref({
  device_id: '', device_type: 'inverter', name: '', host: '127.0.0.1',
  port: 502, protocol: '', location: '', manufacturer: '', model: '',
})

const mockDevices = [
  { device_id:'WT001', device_type:'wind_turbine', name:'1号风机', status:'running', temp:55, vibration:3.2, power:1500, location:'A区', lastMaintenance:'2026-07-15', installDate:'2024-03-01', manufacturer:'Fuhrlander', model:'MM82' },
  { device_id:'WT002', device_type:'wind_turbine', name:'2号风机', status:'running', temp:52, vibration:2.8, power:1480, location:'A区', lastMaintenance:'2026-07-20', installDate:'2024-03-01', manufacturer:'Fuhrlander', model:'MM82' },
  { device_id:'INV001', device_type:'inverter', name:'1号逆变器', status:'running', temp:62, vibration:1.5, power:480, location:'B区', lastMaintenance:'2026-06-30', installDate:'2024-06-15', manufacturer:'华为', model:'SUN2000-330KTL' },
  { device_id:'INV002', device_type:'inverter', name:'2号逆变器', status:'warning', temp:78, vibration:1.8, power:420, location:'B区', lastMaintenance:'2026-07-10', installDate:'2024-06-15', manufacturer:'华为', model:'SUN2000-330KTL' },
  { device_id:'INV003', device_type:'inverter', name:'3号逆变器', status:'fault', temp:85, vibration:2.1, power:0, location:'B区', lastMaintenance:'2026-06-28', installDate:'2024-06-15', manufacturer:'华为', model:'SUN2000-330KTL' },
  { device_id:'TRA001', device_type:'transformer', name:'1号主变', status:'running', temp:68, vibration:0.8, power:3200, location:'C区', lastMaintenance:'2026-08-01', installDate:'2023-09-01', manufacturer:'特变电工', model:'SZ11-5000/35' },
  { device_id:'CBX001', device_type:'combiner_box', name:'1号汇流箱', status:'running', temp:42, vibration:0.3, power:240, location:'B区', lastMaintenance:'2026-07-25', installDate:'2024-06-20', manufacturer:'阳光电源', model:'SPM-16' },
  { device_id:'SVG001', device_type:'svg', name:'1号SVG', status:'running', temp:58, vibration:0.6, power:1500, location:'C区', lastMaintenance:'2026-07-18', installDate:'2024-03-15', manufacturer:'思源', model:'QNSVG-5/35' },
]

const filteredDevices = computed(() => {
  if (!searchText.value) return devices.value
  const s = searchText.value.toLowerCase()
  return devices.value.filter((d: any) =>
    d.name?.toLowerCase().includes(s) || d.device_id?.toLowerCase().includes(s) ||
    d.device_type?.toLowerCase().includes(s) || d.location?.toLowerCase().includes(s) ||
    d.status?.toLowerCase().includes(s)
  )
})

const statusCounts = computed(() => ({
  running: devices.value.filter((d:any) => d.status === 'running').length,
  warning: devices.value.filter((d:any) => d.status === 'warning').length,
  fault: devices.value.filter((d:any) => d.status === 'fault').length,
  offline: devices.value.filter((d:any) => d.status === 'offline').length,
}))

onMounted(async () => {
  loading.value = true
  try { const r = await scadaApi.devices(); devices.value = ((r.data||r) as any[])?.length ? (r.data||r) as any[] : mockDevices } catch { devices.value = mockDevices }
  loading.value = false
})

function queryDevice(row: any) {
  selected.value = row
  querying.value = true
  scadaApi.data(row.device_id).then(r => { deviceData.value = r.data || r }).catch(() => { deviceData.value = row }).finally(() => { querying.value = false })
}

function statusColor(s: string) { return s === 'running' ? 'success' : s === 'warning' ? 'warning' : s === 'fault' ? 'danger' : 'info' }
function statusText(s: string) { return s === 'running' ? '运行中' : s === 'warning' ? '告警' : s === 'fault' ? '故障' : '离线' }
function deviceIcon(type: string) {
  const map: Record<string,string> = { wind_turbine:'🌬', inverter:'⚡', transformer:'🔌', combiner_box:'📦', svg:'🔋' }
  return map[type] || '📡'
}

async function addDevice() {
  if (!newDevice.value.device_id || !newDevice.value.name) {
    ElMessage.warning('请填写设备ID和名称'); return
  }
  adding.value = true
  try {
    await scadaApi.connect({
      device_id: newDevice.value.device_id, device_type: newDevice.value.device_type,
      host: newDevice.value.host, port: newDevice.value.port, mock_mode: true,
    })
    devices.value.unshift({
      ...newDevice.value, status: 'running', temp: 0, vibration: 0, power: 0,
      location: newDevice.value.location || '新接入', lastMaintenance: new Date().toISOString().slice(0, 10),
    })
    ElMessage.success('设备已添加')
    showAddDialog.value = false
    newDevice.value = { device_id: '', device_type: 'inverter', name: '', host: '127.0.0.1', port: 502, protocol: '', location: '', manufacturer: '', model: '' }
  } catch { ElMessage.error('添加失败') }
  adding.value = false
}
</script>

<template>
  <div class="device-page animate-fade-in">
    <div class="stats-row">
      <StatCard title="运行中" :value="statusCounts.running" unit="台" color="#52c41a" trend="up" />
      <StatCard title="告警" :value="statusCounts.warning" unit="台" color="#ff9c40" :trend="statusCounts.warning > 0 ? 'up' : 'flat'" />
      <StatCard title="故障" :value="statusCounts.fault" unit="台" color="#ff4d4f" :trend="statusCounts.fault > 0 ? 'up' : 'flat'" />
      <StatCard title="总计" :value="devices.length" unit="台" color="var(--color-accent)" trend="flat" />
    </div>

    <div class="grid-2col">
      <div class="tech-card">
        <div class="card-header">
          <h4>📡 设备列表</h4>
          <div style="display:flex;gap:8px">
            <el-input v-model="searchText" placeholder="搜索设备..." size="small" clearable style="width:160px" />
            <el-button size="small" type="primary" @click="showAddDialog = true">+ 添加设备</el-button>
          </div>
        </div>
        <el-table :data="filteredDevices" size="small" v-loading="loading" highlight-current-row @row-click="queryDevice" max-height="420">
          <el-table-column label="" width="35">
            <template #default="{ row: r }"><span style="font-size:16px">{{ deviceIcon(r.device_type) }}</span></template>
          </el-table-column>
          <el-table-column prop="device_id" label="设备ID" width="95" />
          <el-table-column prop="name" label="名称" width="95" />
          <el-table-column prop="device_type" label="类型" width="90">
            <template #default="{ row: r }"><el-tag size="small" effect="plain">{{ r.device_type === 'wind_turbine' ? '风机' : r.device_type === 'inverter' ? '逆变器' : r.device_type === 'transformer' ? '变压器' : r.device_type === 'combiner_box' ? '汇流箱' : r.device_type }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="75">
            <template #default="{ row: r }"><el-tag size="small" :type="statusColor(r.status)">{{ statusText(r.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="temp" label="温度(°C)" width="85">
            <template #default="{ row: r }"><span class="font-digital" :style="{color: (r.temp||0) > 80 ? '#ff4d4f' : (r.temp||0) > 65 ? '#ff9c40' : '#52c41a'}">{{ r.temp }}°C</span></template>
          </el-table-column>
          <el-table-column prop="power" label="功率(kW)" width="85">
            <template #default="{ row: r }"><span class="font-digital" :style="{color: r.status==='fault'?'#ff4d4f':'var(--color-accent)'}">{{ r.power }}</span></template>
          </el-table-column>
          <el-table-column prop="location" label="位置" width="60" />
          <el-table-column prop="lastMaintenance" label="上次维保" width="100" />
        </el-table>
      </div>

      <div>
        <div class="tech-card" v-if="selected" v-loading="querying">
          <div class="card-header">
            <h4>🔍 {{ deviceIcon(selected.device_type) }} {{ selected.name || selected.device_id }}</h4>
            <el-tag :type="statusColor(selected.status)">{{ statusText(selected.status) }}</el-tag>
          </div>
          <div class="detail-grid">
            <div class="dg-item" v-for="(v,k) in (deviceData || selected)" :key="k">
              <span class="dgk">{{ k }}</span>
              <span class="dgv" :class="{ 'font-digital': typeof v === 'number' }">{{ typeof v === 'object' ? JSON.stringify(v).slice(0,60) : v }}</span>
            </div>
          </div>
          <div class="quick-actions" style="margin-top:12px">
            <el-button size="small" type="primary" @click="$router.push(`/diagnostic?q=${selected.name}故障排查`)">🔧 智能诊断</el-button>
            <el-button size="small" @click="$router.push(`/scada`)">📊 SCADA数据</el-button>
            <el-button size="small" @click="$router.push('/alarms')">🚨 查看告警</el-button>
          </div>
        </div>

        <div v-else class="tech-card">
          <h4>🔍 设备详情</h4>
          <div class="empty-state">
            <el-icon :size="40" color="rgba(0,240,255,0.15)"><component is="Cpu" /></el-icon>
            <p>点击左侧设备查看详情</p>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showAddDialog" title="添加新设备" width="500px">
      <el-form :model="newDevice" label-width="80px" size="small">
        <el-form-item label="设备ID" required><el-input v-model="newDevice.device_id" placeholder="如: WT005" /></el-form-item>
        <el-form-item label="设备名称" required><el-input v-model="newDevice.name" placeholder="如: 5号风机" /></el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="newDevice.device_type" style="width:100%">
            <el-option label="风电机组" value="wind_turbine" />
            <el-option label="光伏逆变器" value="inverter" />
            <el-option label="变压器" value="transformer" />
            <el-option label="汇流箱" value="combiner_box" />
            <el-option label="SVG无功补偿" value="svg" />
            <el-option label="保护装置" value="protection" />
            <el-option label="储能系统" value="battery" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP地址"><el-input v-model="newDevice.host" /></el-form-item>
        <el-form-item label="端口"><el-input-number v-model="newDevice.port" :min="1" :max="65535" /></el-form-item>
        <el-form-item label="厂商"><el-input v-model="newDevice.manufacturer" placeholder="如: 华为" /></el-form-item>
        <el-form-item label="型号"><el-input v-model="newDevice.model" placeholder="如: SUN2000" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="newDevice.location" placeholder="如: B区-04" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addDevice" :loading="adding">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.device-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.grid-2col { display: grid; grid-template-columns: 1fr 340px; gap: 14px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
  h4 { color: var(--color-accent); font-size: 14px; margin: 0; }
}
.detail-grid { display: flex; flex-direction: column; gap: 2px; max-height: 350px; overflow-y: auto; }
.dg-item { display: flex; gap: 12px; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.04); font-size: 12px; }
.dgk { color: var(--color-accent); min-width: 100px; opacity: 0.85; }
.dgv { color: var(--color-text-secondary); word-break: break-all; }
.quick-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 40px;
  p { margin-top: 10px; font-size: 14px; }
}
h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }
</style>
