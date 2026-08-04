<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { healthCheck } from './api'
import ParticleBackground from './components/ParticleBackground.vue'
import AlarmAlertOverlay from './components/AlarmAlertOverlay.vue'

const router = useRouter()
const route = useRoute()
const systemReady = ref(false)

healthCheck().then(() => { systemReady.value = true }).catch(() => {})

const navItems = [
  { path: '/',          icon: 'Odometer',  label: '总览看板' },
  { path: '/diagnostic', icon: 'ChatDotRound', label: '智能诊断中心' },
  { path: '/scada',     icon: 'Monitor',   label: 'SCADA 数据看板' },
  { path: '/alarms',    icon: 'Bell',      label: '告警管理' },
  { path: '/trace/demo', icon: 'VideoPlay', label: '诊断过程透视' },
  { path: '/knowledge', icon: 'Collection', label: '知识库管理' },
  { path: '/devices',   icon: 'Cpu',       label: '设备状态查询' },
  { path: '/feedback',  icon: 'DataAnalysis', label: '反馈与学习' },
  { path: '/skills',    icon: 'SetUp',     label: '技能管理' },
  { path: '/settings',  icon: 'Setting',   label: '系统设置' },
]

function go(path: string) { router.push(path) }
</script>

<template>
  <div class="app-shell">
    <ParticleBackground />
    <AlarmAlertOverlay />
    <aside class="sidebar">
      <div class="logo" @click="go('/')">
        <span class="logo-icon">⚡</span>
        <span class="logo-text font-digital">驭能</span>
        <span class="logo-badge">{{ systemReady ? '在线' : '...' }}</span>
      </div>
      <nav class="nav-list">
        <div
          v-for="item in navItems" :key="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path || (item.path !== '/' && (item.path.split('/:')[0] ? route.path.startsWith(item.path.split('/:')[0]!) : false)) }"
          @click="go(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </nav>
      <div class="sidebar-footer">
        <div class="status-row">
          <span class="status-dot" :class="{ online: systemReady }"></span>
          <span>{{ systemReady ? 'DeepSeek V4 Pro' : '连接中...' }}</span>
        </div>
        <div class="version">v1.0 · 宁夏新能源智能运维</div>
      </div>
    </aside>
    <div class="main-area">
      <header class="app-header">
        <h2 class="page-title font-digital">{{ route.meta.title }}</h2>
        <div class="header-right">
          <span class="time font-digital">{{ new Date().toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
        </div>
      </header>
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  display: flex; height: 100vh; overflow: hidden;
}
.sidebar {
  width: 220px; background: rgba(10, 22, 40, 0.95);
  border-right: 1px solid rgba(0, 240, 255, 0.1);
  display: flex; flex-direction: column; padding: 16px 0; flex-shrink: 0;
}
.logo {
  display: flex; align-items: center; gap: 8px; padding: 0 16px 16px;
  border-bottom: 1px solid rgba(0, 240, 255, 0.08); cursor: pointer;
  .logo-icon { font-size: 22px; }
  .logo-text { font-size: 20px; color: var(--color-accent); font-weight: 700; }
  .logo-badge { font-size: 10px; color: var(--color-accent); background: var(--color-accent-dim); padding: 2px 8px; border-radius: 8px; }
}
.nav-list { flex: 1; padding: 8px; overflow-y: auto; }
.nav-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 6px; cursor: pointer; color: var(--color-text-secondary);
  font-size: 13px; transition: all 0.2s; margin-bottom: 2px;
  &:hover { background: rgba(0, 240, 255, 0.06); color: var(--color-accent); }
  &.active { background: rgba(0, 240, 255, 0.1); color: var(--color-accent); }
}
.sidebar-footer { padding: 12px 16px; border-top: 1px solid rgba(0, 240, 255, 0.08); font-size: 11px; color: var(--color-text-secondary); }
.status-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #ff4d4f;
  &.online { background: #52c41a; box-shadow: 0 0 6px rgba(82, 196, 26, 0.5); }
}
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.app-header {
  height: 52px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; border-bottom: 1px solid rgba(0, 240, 255, 0.08);
  background: rgba(10, 22, 40, 0.6); flex-shrink: 0;
  .page-title { font-size: 15px; color: var(--color-accent); letter-spacing: 2px; }
  .time { font-size: 13px; color: var(--color-text-secondary); }
}
.page-content { flex: 1; overflow-y: auto; padding: 16px 24px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s, transform 0.3s; }
.fade-enter-from { opacity: 0; transform: translateY(8px); }
.fade-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
