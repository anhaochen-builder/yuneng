<script setup lang="ts">
defineProps<{ title: string; value: string | number; unit?: string; trend?: 'up' | 'down' | 'flat'; color?: string }>()
</script>

<template>
  <div class="stat-card">
    <div class="stat-value font-digital" :style="{ color: color || '#00f0ff' }">
      {{ value }}<span class="stat-unit" v-if="unit">{{ unit }}</span>
    </div>
    <div class="stat-title">{{ title }}</div>
    <div v-if="trend" class="stat-trend" :class="trend">
      <span v-if="trend === 'up'">▲</span>
      <span v-else-if="trend === 'down'">▼</span>
      <span v-else>─</span>
    </div>
  </div>
</template>

<style scoped>
.stat-card { text-align: center; padding: 12px; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-unit { font-size: 12px; opacity: 0.6; margin-left: 4px; }
.stat-title { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.stat-trend { font-size: 14px; margin-top: 2px; }
.stat-trend.up { color: #52c41a; }
.stat-trend.down { color: #ff4d4f; }
.stat-trend.flat { color: #8892a4; }
</style>
