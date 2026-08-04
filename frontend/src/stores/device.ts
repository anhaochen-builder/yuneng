import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useDeviceStore = defineStore('device', () => {
  const devices = ref<Map<string, any>>(new Map())
  const selectedDeviceId = ref<string | null>(null)

  const selectedDevice = computed(() =>
    selectedDeviceId.value ? devices.value.get(selectedDeviceId.value) : null
  )
  const onlineDevices = computed(() =>
    Array.from(devices.value.values()).filter((d: any) => d.status === 'running')
  )

  function updateDeviceStatus(deviceId: string, data: any) {
    devices.value.set(deviceId, { ...devices.value.get(deviceId), ...data, lastUpdated: new Date().toISOString() })
  }

  return { devices, selectedDeviceId, selectedDevice, onlineDevices, updateDeviceStatus }
}, { persist: true })
