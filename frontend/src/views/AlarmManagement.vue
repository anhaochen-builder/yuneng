<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { alarmApi } from '@/api'

const alarms = ref<any[]>([])
const alarmForm = ref({ alarm_id: '', device_id: '', device_type: '', alarm_type: '', alarm_level: 'high', alarm_message: '', current_value: '', threshold: '', auto_diagnose: true })
const submitting = ref(false)
const diagResult = ref<any>(null)

onMounted(async () => {
  try { const r = await alarmApi.health(); } catch {}
})

async function submitAlarm() {
  submitting.value = true
  try {
    const r = await alarmApi.receive(alarmForm.value)
    const data = r.data || r
    alarms.value.unshift({ ...data, time: new Date().toLocaleTimeString() })
    if (data.report) diagResult.value = data
    ElMessage.success('告警已接收' + (data.status === 'DIAGNOSED' ? '并自动诊断完成' : ''))
  } catch { ElMessage.error('告警提交失败') }
  submitting.value = false
}
</script>

<template>
  <div class="alarm-page animate-fade-in">
    <div class="grid-2col">
      <div class="tech-card">
        <h4>🚨 告警接收</h4>
        <el-form :model="alarmForm" label-width="80px" size="small">
          <el-form-item label="告警编号"><el-input v-model="alarmForm.alarm_id" placeholder="ALM-001" /></el-form-item>
          <el-form-item label="设备ID"><el-input v-model="alarmForm.device_id" placeholder="INV003" /></el-form-item>
          <el-form-item label="设备类型"><el-input v-model="alarmForm.device_type" placeholder="逆变器" /></el-form-item>
          <el-form-item label="告警类型"><el-input v-model="alarmForm.alarm_type" placeholder="通讯中断" /></el-form-item>
          <el-form-item label="告警级别">
            <el-select v-model="alarmForm.alarm_level">
              <el-option label="CRITICAL" value="critical" />
              <el-option label="HIGH" value="high" />
              <el-option label="MEDIUM" value="medium" />
              <el-option label="LOW" value="low" />
            </el-select>
          </el-form-item>
          <el-form-item label="告警描述"><el-input v-model="alarmForm.alarm_message" type="textarea" rows="2" placeholder="详细描述..." /></el-form-item>
          <el-form-item label="当前值"><el-input v-model="alarmForm.current_value" placeholder="如: 85°C" /></el-form-item>
          <el-form-item label="阈值"><el-input v-model="alarmForm.threshold" placeholder="如: 75°C" /></el-form-item>
          <el-form-item label="自动诊断"><el-switch v-model="alarmForm.auto_diagnose" /></el-form-item>
          <el-form-item><el-button type="primary" @click="submitAlarm" :loading="submitting">提交告警</el-button></el-form-item>
        </el-form>
      </div>

      <div class="tech-card">
        <h4>📋 告警记录</h4>
        <div v-if="alarms.length" class="alarm-list">
          <div v-for="a in alarms" :key="a.task_id || a.alarm_id" class="alarm-item" :class="a.status">
            <div class="alarm-header">
              <el-tag size="small" :type="a.risk_level === 'CRITICAL' ? 'danger' : a.risk_level === 'HIGH' ? 'warning' : 'info'">{{ a.risk_level || a.status }}</el-tag>
              <span class="alarm-id">{{ a.alarm_id || a.task_id }}</span>
              <span class="alarm-time">{{ a.time }}</span>
            </div>
            <div class="alarm-detail">{{ a.message || a.report?.slice(0, 200) }}</div>
          </div>
        </div>
        <div v-else class="empty-state">暂无告警记录</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.alarm-page { .grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } }
h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 13px; }
.alarm-item { padding: 10px; border-bottom: 1px solid rgba(0, 240, 255, 0.05); font-size: 13px;
  &.DIAGNOSED { border-left: 3px solid #52c41a; }
  &.RECEIVED { border-left: 3px solid var(--color-accent); }
}
.alarm-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.alarm-id { color: var(--color-accent); }
.alarm-time { font-size: 11px; color: var(--color-text-secondary); margin-left: auto; }
.alarm-detail { color: var(--color-text-secondary); font-size: 12px; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 24px; }
</style>
