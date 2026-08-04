<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { healthCheck } from './api'
import ParticleBackground from './components/ParticleBackground.vue'

const router = useRouter()
const route = useRoute()
const systemReady = ref(false)
const now = ref(new Date())

healthCheck().then(() => { systemReady.value = true }).catch(() => {})
setInterval(() => { now.value = new Date() }, 1000)

const navItems = [
  { path: '/',          icon: 'Odometer',  label: '总览看板' },
  { path: '/diagnostic', icon: 'ChatDotRound', label: '智能诊断' },
  { path: '/scada',     icon: 'Monitor',   label: 'SCADA看板' },
  { path: '/alarms',    icon: 'Bell',      label: '告警管理' },
  { path: '/knowledge', icon: 'Collection', label: '知识库' },
  { path: '/devices',   icon: 'Cpu',       label: '设备管理' },
  { path: '/settings',  icon: 'Setting',   label: '系统设置' },
]

function go(path: string) { router.push(path) }
function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="app-shell">
    <ParticleBackground />
    <header class="dashboard-header">
      <div class="header-left">
        <span class="header-status">
          <span class="status-dot" :class="{ online: systemReady }"></span>
          {{ systemReady ? 'DeepSeek V4 Pro' : '连接中...' }}
        </span>
      </div>
      <h1 class="header-title">驭能智能诊断平台</h1>
      <div class="header-right">
        <span class="header-time font-digital">{{ now.toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
      </div>
    </header>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer class="footer-nav">
      <div
        v-for="item in navItems" :key="item.path"
        class="nav-item" :class="{ active: isActive(item.path) }"
        @click="go(item.path)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </div>
    </footer>
  </div>
</template>

<style scoped lang="scss">
.app-shell { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
.dashboard-header {
  display: flex; justify-content: space-between; align-items: center;
  height: 70px; padding: 0 30px; flex-shrink: 0;
  background: linear-gradient(to bottom, rgba(6,30,65,0.8), transparent);
  position: relative;
  &::after {
    content: ''; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
    width: 60%; height: 1px;
    background: linear-gradient(to right, transparent, var(--color-accent), transparent);
  }
}
.header-title {
  font-size: 36px; letter-spacing: 6px;
  background: linear-gradient(to bottom, #fff, #8ba0c8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  text-shadow: none;
}
.header-left, .header-right { display: flex; gap: 16px; font-size: 14px; color: var(--color-text-secondary); align-items: center; }
.header-time { font-size: 22px; color: var(--color-text-primary); font-weight: bold; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; background: #ff4d4f; margin-right: 6px; vertical-align: middle; }
.status-dot.online { background: #52c41a; box-shadow: 0 0 8px rgba(82,196,26,0.5); }
.main-content { flex: 1; overflow: hidden; }
.footer-nav {
  display: flex; justify-content: center; align-items: center; gap: 30px;
  height: 55px; flex-shrink: 0;
  background: linear-gradient(to top, rgba(2, 11, 26, 1), transparent);
}
.nav-item {
  display: flex; align-items: center; gap: 6px; color: var(--color-text-secondary);
  font-size: 15px; cursor: pointer; padding: 8px 16px; transition: all 0.3s; border-bottom: 2px solid transparent;
  &:hover, &.active { color: var(--color-accent); border-bottom-color: var(--color-accent); }
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s, transform 0.3s; }
.fade-enter-from { opacity: 0; transform: translateY(8px); }
.fade-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
