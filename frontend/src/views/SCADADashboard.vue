<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { scadaApi } from '@/api'
import PowerBarChart from '@/components/charts/PowerBarChart.vue'
import EnergyTrendChart from '@/components/charts/EnergyTrendChart.vue'
import SCADATrendChart from '@/components/charts/SCADATrendChart.vue'
import DeviceHealthRadar from '@/components/charts/DeviceHealthRadar.vue'
import EnvironmentPanel from '@/components/EnvironmentPanel.vue'
import StatCard from '@/components/charts/StatCard.vue'

const devices = ref<any[]>([])
const bufferStats = ref({ total_points: 0, capacity: 1800000 })
const scadaForm = ref({ device_id: '', device_type: 'inverter', host: '127.0.0.1', port: 502, protocol: 'modbus', mock_mode: true })
const connecting = ref(false)
const selectedDevice = ref<string | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 实时模拟数据 (实际部署时从 API 获取)
const hours = ref(Array.from({ length: 24 }, (_, i) => ({ hour: `${i}:00`, power: 200 + Math.random() * 400 })))
const days = ref(['周一', '周二', '周三', '周四', '周五', '周六', '周日'])
const predicted = ref([420, 450, 380, 500, 460, 480, 430])
const actual = ref([410, 440, 390, 490, 470, 475, 445])

const tsData = ref(Array.from({ length: 20 }, (_, i) => ({
  time: `${String(i).padStart(2, '0')}:00`,
  power: 300 + Math.random() * 200,
  current: 15 + Math.random() * 10,
  temp: 55 + Math.random() * 30,
  wind: 5 + Math.random() * 8,
})))

const healthScores = ref({ rpm: 85, temp: 72, vibration: 68, voltage: 90, oilTemp: 78 })
const envData = ref({ temperature: 25.6, humidity: 48, irradiance: 850, windSpeed: 6.8 })

onMounted(async () => {
  await refreshData()
  refreshTimer = setInterval(refreshData, 15000)
})

onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })

async function refreshData() {
  try { const r = await scadaApi.devices(); devices.value = (r.data || r) as any[] } catch {}
  try { const r = await scadaApi.bufferStats(); bufferStats.value = r.data || r } catch {}

  // 更新模拟数据
  hours.value = Array.from({ length: 24 }, (_, i) => ({ hour: `${i}:00`, power: 200 + Math.random() * 400 }))
  tsData.value = Array.from({ length: 20 }, (_, i) => ({
    time: `${String(i).padStart(2, '0')}:00`,
    power: 300 + Math.random() * 200,
    current: 15 + Math.random() * 10,
    temp: 55 + Math.random() * 15,
    wind: 5 + Math.random() * 8,
  }))
  healthScores.value = { rpm: 80 + Math.random() * 10, temp: 65 + Math.random() * 15, vibration: 60 + Math.random() * 20, voltage: 85 + Math.random() * 10, oilTemp: 70 + Math.random() * 15 }
}

async function connectDevice() {
  connecting.value = true
  try {
    await scadaApi.connect(scadaForm.value)
    ElMessage.success('设备连接成功')
    await refreshData()
  } catch { ElMessage.error('连接失败，请检查设备地址和协议') }
  connecting.value = false
}

function selectDevice(deviceId: string) {
  selectedDevice.value = deviceId
  ElMessage.info(`已选中设备: ${deviceId}`)
}

const protoOptions = [
  { label: 'Modbus TCP', value: 'modbus' },
  { label: 'IEC 61850', value: 'iec61850' },
  { label: 'OPC UA', value: 'opcua' },
]

const typeOptions = [
  { label: '逆变器', value: 'inverter' },
  { label: '风机', value: 'wind_turbine' },
  { label: '变压器', value: 'transformer' },
  { label: '汇流箱', value: 'combiner_box' },
]
</script>

<template>
  <div class="scada-page animate-fade-in">
    <!-- 顶部统计 -->
    <div class="stats-row">
      <StatCard title="已连接设备" :value="devices.filter((d:any)=>d.status==='connected'||d.status==='running').length" unit="台" color="#00f0ff" trend="up" />
      <StatCard title="当日发电量" value="2,847" unit="kWh" color="#00d4aa" trend="up" />
      <StatCard title="设备健康度" :value="85" unit="%" color="#7b68ee" trend="flat" />
      <StatCard title="功率预测准确率" :value="92" unit="%" color="#ff9c40" trend="up" />
      <StatCard title="当日告警" value="6" unit="条" color="#ff4d4f" trend="down" />
    </div>

    <!-- 图表区域 -->
    <div class="grid-2col">
      <div class="tech-card">
        <h4>📊 24h 实时功率</h4>
        <PowerBarChart :data="hours" />
      </div>
      <div class="tech-card">
        <h4>📈 发电量趋势 (预测 vs 实际)</h4>
        <EnergyTrendChart :predicted="predicted" :actual="actual" :labels="days" />
      </div>
    </div>

    <div class="grid-2col">
      <div class="tech-card">
        <h4>📉 SCADA 时序趋势</h4>
        <SCADATrendChart :timeSeries="tsData" />
      </div>
      <div class="tech-card">
        <h4>🩺 设备健康度雷达</h4>
        <DeviceHealthRadar :scores="healthScores" />
      </div>
    </div>

    <!-- 底部: 环境 + 设备列表 + 连接 -->
    <div class="grid-3col">
      <EnvironmentPanel :envData="envData" />

      <div class="tech-card">
        <h4>📡 已连接设备</h4>
        <el-table :data="devices" size="small" v-if="devices.length" highlight-current-row @row-click="(row:any) => selectDevice(row.device_id)">
          <el-table-column prop="device_id" label="设备ID" width="90" />
          <el-table-column prop="device_type" label="类型" width="80" />
          <el-table-column prop="protocol" label="协议" width="90" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status==='connected'||row.status==='running'?'success':'warning'">
                {{ row.status || 'connected' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数据点" width="70">
            <template #default><span class="font-digital" style="color:var(--color-accent);font-size:12px">1.8M</span></template>
          </el-table-column>
        </el-table>
        <div v-else class="empty-state">暂无连接设备，请添加设备连接</div>
      </div>

      <div class="tech-card">
        <h4>🔌 添加设备</h4>
        <el-form :model="scadaForm" label-width="70px" size="small">
          <el-form-item label="设备ID"><el-input v-model="scadaForm.device_id" placeholder="如: INV003" /></el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="scadaForm.device_type">
              <el-option v-for="o in typeOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="协议类型">
            <el-select v-model="scadaForm.protocol">
              <el-option v-for="o in protoOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="地址"><el-input v-model="scadaForm.host" placeholder="127.0.0.1" /></el-form-item>
          <el-form-item label="端口"><el-input-number v-model="scadaForm.port" :min="1" :max="65535" /></el-form-item>
          <el-form-item label="模拟模式"><el-switch v-model="scadaForm.mock_mode" /></el-form-item>
          <el-form-item>
            <el-button type="primary" @click="connectDevice" :loading="connecting" style="width:100%">
              {{ connecting ? '连接中...' : '连接设备' }}
            </el-button>
          </el-form-item>
        </el-form>
        <div class="buffer-info">
          <span>环形缓冲区: {{ ((bufferStats.total_points || 0) / 10000).toFixed(1) }}万 / {{ (bufferStats.capacity / 10000).toFixed(1) }}万</span>
          <el-progress :percentage="Math.min(((bufferStats.total_points||0)/bufferStats.capacity)*100, 100)" :stroke-width="4" color="var(--color-accent)" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.scada-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.stats-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }

.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.grid-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }

h4 { color: var(--color-accent); margin-bottom: 10px; font-size: 13px; font-weight: 600; }

.empty-state { text-align: center; color: var(--color-text-secondary); padding: 32px; font-size: 13px; }

.buffer-info {
  margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(0,240,255,0.06);
  font-size: 11px; color: var(--color-text-secondary);
}
</style>
