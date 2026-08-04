<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { scadaApi } from '@/api'
import PowerBarChart from '@/components/charts/PowerBarChart.vue'
import EnergyTrendChart from '@/components/charts/EnergyTrendChart.vue'
import SCADATrendChart from '@/components/charts/SCADATrendChart.vue'
import DeviceHealthRadar from '@/components/charts/DeviceHealthRadar.vue'
import EnvironmentPanel from '@/components/EnvironmentPanel.vue'

const devices = ref<any[]>([])
const bufferStats = ref({ total_points: 0, capacity: 1800000 })
const scadaForm = ref({ device_id: '', device_type: 'inverter', host: '127.0.0.1', port: 502, mock_mode: true })
const connecting = ref(false)

const hours = Array.from({ length: 24 }, (_, i) => ({ hour: `${i}:00`, power: 200 + Math.random() * 400 }))
const days = Array.from({ length: 7 }, (_, i) => `D${i + 1}`)
const predicted = [420, 450, 380, 500, 460, 480, 430]
const actual = [410, 440, 390, 490, 470, 475, 445]

const tsData = Array.from({ length: 20 }, (_, i) => ({
  time: `${String(i).padStart(2, '0')}:00`,
  power: 300 + Math.random() * 200,
  current: 15 + Math.random() * 10,
  temp: 55 + Math.random() * 30,
  wind: 5 + Math.random() * 8,
}))

const healthScores = { rpm: 85, temp: 72, vibration: 68, voltage: 90, oilTemp: 78 }
const envData = { temperature: 25.6, humidity: 48, irradiance: 850, windSpeed: 6.8 }

onMounted(async () => {
  try { const r = await scadaApi.devices(); devices.value = (r.data || r) as any[] } catch {}
  try { const r = await scadaApi.bufferStats(); bufferStats.value = r.data || r } catch {}
})

async function connectDevice() {
  connecting.value = true
  try { await scadaApi.connect(scadaForm.value); ElMessage.success('连接成功') } catch { ElMessage.error('连接失败') }
  connecting.value = false
}
</script>

<template>
  <div class="scada-page animate-fade-in">
    <div class="stats-row">
      <div class="stat-card" v-for="s in [
        { label: '已连接设备', value: devices.length, color: '#00f0ff' },
        { label: '当日发电量', value: '2,847', unit: 'kWh', color: '#00d4aa' },
        { label: '设备健康度', value: '85', unit: '%', color: '#7b68ee' },
        { label: '功率预测准确率', value: '92', unit: '%', color: '#ff9c40' },
      ]" :key="s.label">
        <div class="stat-val font-digital" :style="{ color: s.color }">{{ s.value }}<span class="stat-unit" v-if="(s as any).unit">{{ (s as any).unit }}</span></div>
        <div class="stat-lbl">{{ s.label }}</div>
      </div>
    </div>

    <div class="grid-2col">
      <div class="tech-card"><h4>📊 24h 实时功率</h4><PowerBarChart :data="hours" /></div>
      <div class="tech-card"><h4>📈 发电量趋势</h4><EnergyTrendChart :predicted="predicted" :actual="actual" :labels="days" /></div>
    </div>

    <div class="grid-2col">
      <div class="tech-card"><h4>📉 SCADA 双轴趋势</h4><SCADATrendChart :timeSeries="tsData" /></div>
      <div class="tech-card"><h4>🩺 设备健康度</h4><DeviceHealthRadar :scores="healthScores" /></div>
    </div>

    <div class="grid-2col">
      <EnvironmentPanel :envData="envData" />
      <div class="tech-card">
        <h4>📡 已连接设备</h4>
        <el-table :data="devices" size="small" v-if="devices.length">
          <el-table-column prop="device_id" label="设备ID" />
          <el-table-column prop="device_type" label="类型" />
          <el-table-column prop="protocol" label="协议" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }"><el-tag size="small" :type="row.status === 'connected' ? 'success' : 'warning'">{{ row.status || 'connected' }}</el-tag></template>
          </el-table-column>
        </el-table>
        <div v-else class="empty-state">暂无连接设备</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.scada-page { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { background: rgba(10, 22, 40, 0.7); border: 1px solid rgba(0, 240, 255, 0.1); border-radius: 6px; padding: 16px; text-align: center; }
.stat-val { font-size: 24px; font-weight: 700; }
.stat-unit { font-size: 12px; opacity: 0.6; margin-left: 4px; }
.stat-lbl { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
h4 { color: var(--color-accent); margin-bottom: 8px; font-size: 13px; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 24px; }
</style>
