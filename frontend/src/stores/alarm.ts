import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Alarm } from '@/types'

export const useAlarmStore = defineStore('alarm', () => {
  const alarms = ref<Alarm[]>([])
  const unreadCount = ref(0)
  const levelPriority: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 }
  const wsConnected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return
    const base = (import.meta as any).env?.VITE_API_BASE_URL || ''
    const wsUrl = base.replace(/^http/, 'ws') + '/ws/alarms'
    try {
      ws = new WebSocket(wsUrl)
      ws.onopen = () => { wsConnected.value = true; if (reconnectTimer) clearTimeout(reconnectTimer) }
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'alarm') addAlarm(msg.data as Alarm)
        } catch { /* ignore non-alarm messages */ }
      }
      ws.onclose = () => {
        wsConnected.value = false
        reconnectTimer = setTimeout(connectWebSocket, 5000)
      }
      ws.onerror = () => { ws?.close() }
    } catch {
      reconnectTimer = setTimeout(connectWebSocket, 10000)
    }
  }

  function addAlarm(alarm: Alarm) {
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

  connectWebSocket()

  return { alarms, unreadCount, wsConnected, addAlarm, markAsRead }
}, { persist: true })
