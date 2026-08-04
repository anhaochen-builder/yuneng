<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { scadaApi, alarmApi } from '@/api'

interface DeviceCard {
  id: string; name: string; type: string; status: 'normal' | 'warning' | 'critical' | 'offline'
  temp: number; vibration: number; power: number; rpm: number; location: string
  lastSeen: string; alerts: number
}

const devices = ref<DeviceCard[]>([])
const filterStatus = ref('all')
const filterType = ref('all')
const sortBy = ref('name')
let timer: any = null
const selectedDevice = ref<DeviceCard | null>(null)
const showDetail = ref(false)
const pollingInterval = ref(5000)
const isPolling = ref(true)

// 模拟电厂设备 — 实际对接 SCADA API 替换
const mockDevices: DeviceCard[] = [
  { id:'WT001', name:'1号风机', type:'风电机组', status:'normal', temp:55, vibration:3.2, power:1500, rpm:14, location:'A区-01', lastSeen:'3秒前', alerts:0 },
  { id:'WT002', name:'2号风机', type:'风电机组', status:'warning', temp:72, vibration:7.8, power:1420, rpm:13, location:'A区-02', lastSeen:'5秒前', alerts:2 },
  { id:'WT003', name:'3号风机', type:'风电机组', status:'normal', temp:52, vibration:2.8, power:1480, rpm:14, location:'A区-03', lastSeen:'2秒前', alerts:0 },
  { id:'WT004', name:'4号风机', type:'风电机组', status:'critical', temp:89, vibration:12.5, power:0, rpm:0, location:'A区-04', lastSeen:'1秒前', alerts:5 },
  { id:'INV001', name:'1号逆变器', type:'光伏逆变器', status:'normal', temp:62, vibration:1.5, power:480, rpm:0, location:'B区-01', lastSeen:'4秒前', alerts:0 },
  { id:'INV002', name:'2号逆变器', type:'光伏逆变器', status:'warning', temp:78, vibration:1.8, power:420, rpm:0, location:'B区-02', lastSeen:'3秒前', alerts:1 },
  { id:'INV003', name:'3号逆变器', type:'光伏逆变器', status:'normal', temp:58, vibration:1.2, power:495, rpm:0, location:'B区-03', lastSeen:'2秒前', alerts:0 },
  { id:'TRA001', name:'1号主变', type:'变压器', status:'normal', temp:68, vibration:0.8, power:3200, rpm:0, location:'C区-01', lastSeen:'1秒前', alerts:0 },
  { id:'TRA002', name:'2号箱变', type:'变压器', status:'normal', temp:65, vibration:0.6, power:2800, rpm:0, location:'C区-02', lastSeen:'3秒前', alerts:0 },
  { id:'BAT001', name:'1号储能舱', type:'储能系统', status:'normal', temp:35, vibration:0.3, power:800, rpm:0, location:'D区-01', lastSeen:'2秒前', alerts:0 },
  { id:'SVG001', name:'SVG补偿器', type:'无功补偿', status:'normal', temp:45, vibration:0.5, power:200, rpm:0, location:'E区-01', lastSeen:'4秒前', alerts:0 },
  { id:'PROT01', name:'线路保护A', type:'保护装置', status:'normal', temp:40, vibration:0.2, power:0, rpm:0, location:'F区-01', lastSeen:'1秒前', alerts:0 },
]

const stats = computed(() => ({
  total: devices.value.length,
  normal: devices.value.filter(d => d.status === 'normal').length,
  warning: devices.value.filter(d => d.status === 'warning').length,
  critical: devices.value.filter(d => d.status === 'critical').length,
  offline: devices.value.filter(d => d.status === 'offline').length,
  totalAlerts: devices.value.reduce((s, d) => s + d.alerts, 0),
}))

const typeList = computed(() => [...new Set(devices.value.map(d => d.type))])

const filteredDevices = computed(() => {
  let list = devices.value
  if (filterStatus.value !== 'all') list = list.filter(d => d.status === filterStatus.value)
  if (filterType.value !== 'all') list = list.filter(d => d.type === filterType.value)
  list.sort((a, b) => {
    if (sortBy.value === 'status') return ['critical','warning','normal','offline'].indexOf(a.status) - ['critical','warning','normal','offline'].indexOf(b.status)
    if (sortBy.value === 'alerts') return b.alerts - a.alerts
    return a.id.localeCompare(b.id)
  })
  return list
})

function fetchDevices() {
  // 模拟数据微调 — 实际对接 scadaApi.devices()
  devices.value = mockDevices.map(d => ({
    ...d,
    temp: d.temp + (Math.random() - 0.5) * 3,
    vibration: Math.max(0, d.vibration + (Math.random() - 0.5) * 0.5),
    power: Math.max(0, d.power + (Math.random() - 0.5) * 20),
    lastSeen: `${Math.floor(Math.random() * 10)}秒前`,
    status: d.status === 'critical' ? (Math.random() > 0.5 ? 'critical' : 'critical') : d.status,
  } as DeviceCard))
}

function getStatusColor(s: string) { return { normal:'#52c41a', warning:'#ff9c40', critical:'#ff4d4f', offline:'#8ba0c8' }[s] || '#8ba0c8' }
function getStatusText(s: string) { return { normal:'正常', warning:'告警', critical:'故障', offline:'离线' }[s] || s }
function togglePolling() { isPolling.value = !isPolling.value }
function formatTemp(t: number) { return t > 80 ? '#ff4d4f' : t > 65 ? '#ff9c40' : '#52c41a' }

async function triggerAlarm(device: DeviceCard) {
  try {
    await alarmApi.receive({
      alarm_id: `ALM-${device.id}-${Date.now()}`,
      device_id: device.id,
      device_type: device.type,
      alarm_type: device.status === 'critical' ? '故障停机' : '参数异常',
      alarm_level: device.status,
      alarm_message: `${device.name} ${device.status === 'critical' ? '严重故障，已自动停机' : '运行参数偏离正常范围'}`,
      current_value: `温度${device.temp.toFixed(1)}°C / 振动${device.vibration.toFixed(1)}mm/s`,
      threshold: '温度<70°C / 振动<7mm/s',
      auto_diagnose: true,
    })
  } catch {}
}

onMounted(() => {
  fetchDevices()
  if (isPolling.value) {
    timer = setInterval(fetchDevices, pollingInterval.value)
  }
})

onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="monitor-page animate-fade-in">
    <!-- 统计条 -->
    <div class="stats-bar">
      <div class="stat-chip" v-for="s in [
        { label:'设备总数', value:stats.total, color:'var(--color-accent)' },
        { label:'正常运行', value:stats.normal, color:'#52c41a' },
        { label:'告警中', value:stats.warning, color:'#ff9c40' },
        { label:'故障停机', value:stats.critical, color:'#ff4d4f' },
        { label:'离线', value:stats.offline, color:'#8ba0c8' },
        { label:'今日告警', value:stats.totalAlerts, color:'#ff9c40' },
      ]" :key="s.label">
        <span class="sc-val font-digital" :style="{color:s.color}">{{ s.value }}</span>
        <span class="sc-lbl">{{ s.label }}</span>
      </div>
      <div class="poll-controls">
        <el-switch v-model="isPolling" @change="togglePolling" active-text="自动刷新" size="small" />
        <span class="poll-interval" v-if="isPolling">每{{ pollingInterval / 1000 }}s</span>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-radio-group v-model="filterStatus" size="small">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="normal">正常</el-radio-button>
        <el-radio-button value="warning">告警</el-radio-button>
        <el-radio-button value="critical">故障</el-radio-button>
        <el-radio-button value="offline">离线</el-radio-button>
      </el-radio-group>
      <el-select v-model="filterType" size="small" placeholder="设备类型" clearable style="width:140px">
        <el-option label="全部类型" value="all" />
        <el-option v-for="t in typeList" :key="t" :label="t" :value="t" />
      </el-select>
      <el-select v-model="sortBy" size="small" style="width:120px">
        <el-option label="按编号" value="name" />
        <el-option label="按状态" value="status" />
        <el-option label="按告警数" value="alerts" />
      </el-select>
      <span class="filter-count">显示 {{ filteredDevices.length }} / {{ devices.length }} 台设备</span>
    </div>

    <!-- 设备网格 -->
    <div class="device-grid">
      <div
        v-for="d in filteredDevices" :key="d.id"
        class="device-card" :class="d.status"
        @click="selectedDevice = d; showDetail = true"
      >
        <div class="dc-header">
          <span class="dc-dot" :style="{background:getStatusColor(d.status)}" :class="{ 'pulse-glow': d.status === 'critical' }"></span>
          <span class="dc-id font-digital">{{ d.id }}</span>
          <el-tag size="small" :type="d.status === 'normal' ? 'success' : d.status === 'warning' ? 'warning' : d.status === 'critical' ? 'danger' : 'info'">
            {{ getStatusText(d.status) }}
          </el-tag>
        </div>
        <div class="dc-name">{{ d.name }}</div>
        <div class="dc-type">{{ d.type }} · {{ d.location }}</div>
        <div class="dc-metrics">
          <div class="dm-item"><span class="dm-label">温度</span><span class="dm-val font-digital" :style="{color:formatTemp(d.temp)}">{{ d.temp.toFixed(1) }}°C</span></div>
          <div class="dm-item"><span class="dm-label">振动</span><span class="dm-val font-digital" :style="{color:d.vibration>7?'#ff4d4f':'#52c41a'}">{{ d.vibration.toFixed(1) }}mm/s</span></div>
          <div class="dm-item" v-if="d.power > 0"><span class="dm-label">功率</span><span class="dm-val font-digital">{{ d.power.toFixed(0) }}kW</span></div>
          <div class="dm-item" v-if="d.rpm > 0"><span class="dm-label">转速</span><span class="dm-val font-digital">{{ d.rpm }}rpm</span></div>
        </div>
        <div class="dc-footer">
          <span class="dc-time">{{ d.lastSeen }}</span>
          <span v-if="d.alerts > 0" class="dc-alerts">{{ d.alerts }}条告警</span>
          <el-button v-if="d.status !== 'normal'" size="small" type="primary" text @click.stop="triggerAlarm(d)">触发诊断</el-button>
        </div>
      </div>
    </div>

    <!-- 设备详情弹窗 -->
    <el-dialog v-model="showDetail" :title="`${selectedDevice?.name} (${selectedDevice?.id})`" width="500px" :close-on-click-modal="true">
      <div v-if="selectedDevice" class="detail-content">
        <div class="dd-row"><span class="dd-label">设备类型</span><span>{{ selectedDevice.type }}</span></div>
        <div class="dd-row"><span class="dd-label">位置</span><span>{{ selectedDevice.location }}</span></div>
        <div class="dd-row"><span class="dd-label">运行状态</span><span :style="{color:getStatusColor(selectedDevice.status)}">{{ getStatusText(selectedDevice.status) }}</span></div>
        <div class="dd-row"><span class="dd-label">温度</span><span :style="{color:formatTemp(selectedDevice.temp)}">{{ selectedDevice.temp.toFixed(1) }}°C</span></div>
        <div class="dd-row"><span class="dd-label">振动</span><span>{{ selectedDevice.vibration.toFixed(1) }} mm/s</span></div>
        <div class="dd-row"><span class="dd-label">功率</span><span>{{ selectedDevice.power.toFixed(0) }} kW</span></div>
        <div class="dd-row"><span class="dd-label">转速</span><span>{{ selectedDevice.rpm }} rpm</span></div>
        <div class="dd-row"><span class="dd-label">最近通讯</span><span>{{ selectedDevice.lastSeen }}</span></div>
        <div class="dd-row"><span class="dd-label">历史告警</span><span>{{ selectedDevice.alerts }} 条</span></div>
      </div>
      <template #footer>
        <el-button @click="selectedDevice = null; showDetail = false">关闭</el-button>
        <el-button type="primary" v-if="selectedDevice && selectedDevice.status !== 'normal'" @click="triggerAlarm(selectedDevice); selectedDevice = null; showDetail = false">触发 AI 诊断</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.monitor-page { display: flex; flex-direction: column; gap: 12px; height: calc(100vh - 130px); padding: 8px 16px; overflow-y: auto; }

.stats-bar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.stat-chip { padding: 8px 16px; background: rgba(10,22,40,0.5); border: 1px solid rgba(0,240,255,0.08); border-radius: 6px; text-align: center; min-width: 80px; }
.sc-val { font-size: 20px; font-weight: 700; display: block; }
.sc-lbl { font-size: 11px; color: var(--color-text-secondary); }
.poll-controls { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.poll-interval { font-size: 12px; color: var(--color-text-secondary); }

.filter-bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; padding: 8px 0; }
.filter-count { font-size: 12px; color: var(--color-text-secondary); margin-left: auto; }

.device-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.device-card {
  background: rgba(10,22,40,0.5); border: 1px solid rgba(0,240,255,0.08); border-radius: 8px;
  padding: 14px; cursor: pointer; transition: all 0.2s;
  &:hover { border-color: var(--color-accent); transform: translateY(-2px); }
  &.critical { border-color: rgba(255,77,79,0.3); background: rgba(255,77,79,0.05); }
  &.warning { border-color: rgba(255,156,64,0.3); }
}
.dc-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dc-id { font-size: 12px; color: var(--color-accent); }
.dc-name { font-size: 15px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 2px; }
.dc-type { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 10px; }
.dc-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px; }
.dm-item { padding: 6px 8px; background: rgba(0,240,255,0.03); border-radius: 4px; text-align: center; }
.dm-label { font-size: 10px; color: var(--color-text-secondary); display: block; }
.dm-val { font-size: 14px; font-weight: 600; }
.dc-footer { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--color-text-secondary); }
.dc-alerts { color: #ff4d4f; font-weight: 600; }

.detail-content { display: flex; flex-direction: column; gap: 6px; }
.dd-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.05); font-size: 13px; }
.dd-label { color: var(--color-text-secondary); }
</style>
