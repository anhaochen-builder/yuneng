<script setup lang="ts">
defineProps<{ envData: { temperature: number; humidity: number; irradiance: number; windSpeed: number } }>()
</script>

<template>
  <div class="env-panel tech-card">
    <h4>🌤 环境监测</h4>
    <div class="env-grid">
      <div class="env-item"><span class="env-icon">🌡</span><span class="env-val font-digital">{{ envData.temperature }}°C</span><span class="env-lbl">温度</span></div>
      <div class="env-item"><span class="env-icon">💧</span><span class="env-val font-digital">{{ envData.humidity }}%</span><span class="env-lbl">湿度</span></div>
      <div class="env-item"><span class="env-icon">☀</span><span class="env-val font-digital">{{ envData.irradiance }}</span><span class="env-lbl">辐照度 W/m²</span></div>
      <div class="env-item"><span class="env-icon">💨</span><span class="env-val font-digital">{{ envData.windSpeed }}</span><span class="env-lbl">风速 m/s</span></div>
    </div>
  </div>
</template>

<style scoped>
.env-panel { h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 13px; } }
.env-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.env-item { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 8px; background: rgba(0,240,255,0.04); border-radius: 6px; }
.env-icon { font-size: 20px; }
.env-val { font-size: 18px; color: var(--color-accent); }
.env-lbl { font-size: 10px; color: var(--color-text-secondary); }
</style>
