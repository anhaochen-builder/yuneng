<script setup lang="ts">
import { useAlarmStore } from '@/stores/alarm'
import { useRouter } from 'vue-router'
import { riskLabel } from '@/utils/labels'

const alarmStore = useAlarmStore()
const router = useRouter()

function goAlarms() { router.push('/alarms') }
</script>

<template>
  <div v-if="alarmStore.alarms.filter(a => !a.read).length" class="alarm-overlay">
    <div v-for="a in alarmStore.alarms.filter(a => !a.read).slice(0, 3)" :key="a.id" class="alarm-toast" :class="a.risk_level || a.levelDisplay">
      <div class="toast-header">
        <el-tag size="small" :type="(a.risk_level || a.levelDisplay) === 'critical' ? 'danger' : 'warning'">{{ riskLabel(a.risk_level || a.levelDisplay || '') }}</el-tag>
        <span class="toast-device">{{ a.device_id }}</span>
        <el-button size="small" text @click="alarmStore.markAsRead(a.id); goAlarms()">查看</el-button>
        <el-button size="small" text @click="alarmStore.markAsRead(a.id)">✕</el-button>
      </div>
      <div class="toast-msg">{{ a.message || a.report?.slice(0, 150) }}</div>
    </div>
  </div>
</template>

<style scoped>
.alarm-overlay { position: fixed; top: 60px; right: 16px; z-index: 9998; display: flex; flex-direction: column; gap: 8px; max-width: 380px; }
.alarm-toast { padding: 12px 16px; border-radius: 8px; border: 1px solid; animation: slideIn 0.3s ease-out;
  &.critical { background: rgba(255, 77, 79, 0.15); border-color: rgba(255, 77, 79, 0.4); }
  &.high { background: rgba(255, 156, 64, 0.15); border-color: rgba(255, 156, 64, 0.4); }
  &.medium { background: rgba(0, 240, 255, 0.1); border-color: rgba(0, 240, 255, 0.3); }
}
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.toast-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.toast-device { font-size: 13px; color: var(--color-text-primary); }
.toast-msg { font-size: 12px; color: var(--color-text-secondary); line-height: 1.5; }
</style>
