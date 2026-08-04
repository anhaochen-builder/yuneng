import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAlarmStore = defineStore('alarm', () => {
  const alarms = ref<any[]>([])
  const unreadCount = ref(0)
  const levelPriority: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 }

  function addAlarm(alarm: any) {
    alarms.value.unshift({
      ...alarm, id: alarm.alarmId || 'alarm_' + Date.now(),
      read: false, receivedAt: new Date().toISOString(),
    })
    alarms.value.sort((a, b) => (levelPriority[b.levelDisplay] || 0) - (levelPriority[a.levelDisplay] || 0))
    unreadCount.value++
  }

  function markAsRead(alarmId: string) {
    const a = alarms.value.find(x => x.id === alarmId)
    if (a) { a.read = true; unreadCount.value = Math.max(0, unreadCount.value - 1) }
  }

  return { alarms, unreadCount, addAlarm, markAsRead }
}, { persist: true })
