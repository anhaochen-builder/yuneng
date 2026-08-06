import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Device } from '@/types'

export const useDeviceStore = defineStore('device', () => {
  const devices = ref<Map<string, Device>>(new Map())
  const selectedDeviceId = ref<string | null>(null)

  const selectedDevice = computed(() =>
    selectedDeviceId.value ? devices.value.get(selectedDeviceId.value) ?? null : null
  )
  const onlineDevices = computed(() =>
    Array.from(devices.value.values()).filter((d) => d.status === 'running')
  )

  function updateDeviceStatus(deviceId: string, data: Partial<Device>) {
    const existing = devices.value.get(deviceId)
    devices.value.set(deviceId, { ...existing, ...data, lastUpdated: new Date().toISOString() } as Device)
  }

  return { devices, selectedDeviceId, selectedDevice, onlineDevices, updateDeviceStatus }
}, { persist: true })
