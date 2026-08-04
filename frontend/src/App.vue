<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { healthCheck } from './api'
import AlarmAlertOverlay from './components/AlarmAlertOverlay.vue'

const router = useRouter()
const route = useRoute()
const systemReady = ref(false)
const now = ref(new Date())
let clockTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try { await healthCheck(); systemReady.value = true } catch { systemReady.value = true /* demo mode */ }
  clockTimer = setInterval(() => { now.value = new Date() }, 1000)
})

onUnmounted(() => { if (clockTimer) clearInterval(clockTimer) })

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
    <!-- 效果图背景层 -->
    <div class="effect-bg"></div>

    <!-- 告警浮层 -->
    <AlarmAlertOverlay />

    <!-- 顶部栏 -->
    <header class="dashboard-header">
      <div class="header-left">
        <span class="logo-icon">⚡</span>
        <span class="header-status">
          <span class="status-dot" :class="{ online: systemReady }"></span>
          <span class="status-label">{{ systemReady ? '系统在线' : '连接中...' }}</span>
        </span>
        <span class="header-divider">|</span>
        <span class="header-model">{{ systemReady ? 'DeepSeek V4 Pro' : '初始化中' }}</span>
      </div>

      <h1 class="header-title">
        <span class="title-icon">🔋</span>
        驭能智能诊断平台
      </h1>

      <div class="header-right">
        <span class="header-date">{{ now.toLocaleDateString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit', weekday:'short' }) }}</span>
        <span class="header-time font-digital">{{ now.toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
        <el-button class="settings-btn" circle size="small" @click="go('/settings')">
          <el-icon><component is="Setting" /></el-icon>
        </el-button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 底部导航栏 -->
    <footer class="footer-nav">
      <div class="nav-inner">
        <div
          v-for="item in navItems" :key="item.path"
          class="nav-item" :class="{ active: isActive(item.path) }"
          @click="go(item.path)"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  display: flex; flex-direction: column; height: 100vh; overflow: hidden;
  position: relative; z-index: 1;
}

// ── 效果图背景层 ──
.effect-bg {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 0;
  background-image: url('/effect-bg.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

// ── 顶部栏 (匹配效果图顶部深蓝色调) ──
.dashboard-header {
  display: flex; justify-content: space-between; align-items: center;
  height: 68px; padding: 0 24px; flex-shrink: 0; z-index: 100;
  background: linear-gradient(to bottom, rgba(1, 20, 56, 0.88) 0%, rgba(2, 32, 72, 0.30) 90%, transparent 100%);
  backdrop-filter: blur(10px);
  position: relative;

  &::after {
    content: ''; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
    width: 70%; height: 1px;
    background: linear-gradient(to right, transparent, rgba(48, 167, 209, 0.35), transparent);
  }
}

.header-title {
  font-size: 30px; letter-spacing: 8px; font-weight: 700;
  background: linear-gradient(180deg, #E8ECF1 0%, #8EC8E0 50%, #3A90C0 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  position: absolute; left: 50%; transform: translateX(-50%);
  filter: drop-shadow(0 0 14px rgba(48, 167, 209, 0.45));
  white-space: nowrap;

  .title-icon { font-size: 26px; margin-right: 4px; -webkit-text-fill-color: initial; }
}

.header-left {
  display: flex; align-items: center; gap: 12px; z-index: 1;

  .logo-icon { font-size: 22px; }
  .status-label { font-size: 13px; color: var(--color-text-secondary); }
  .header-divider { color: rgba(255,255,255,0.12); font-size: 18px; }
  .header-model { font-size: 12px; color: var(--color-accent); opacity: 0.75; letter-spacing: 0.5px; }
}

.header-right {
  display: flex; align-items: center; gap: 16px; z-index: 1;

  .header-date { font-size: 13px; color: var(--color-text-secondary); }
  .header-time { font-size: 21px; color: var(--color-text-primary); font-weight: bold; letter-spacing: 1px; }
  .settings-btn {
    background: rgba(48, 167, 209, 0.10); border: 1px solid rgba(48, 167, 209, 0.25); color: var(--color-accent);
    &:hover { background: rgba(48, 167, 209, 0.20); border-color: var(--color-accent); }
  }
}

.status-dot {
  width: 8px; height: 8px; border-radius: 50%; display: inline-block;
  background: #ff4d4f; margin-right: 2px; vertical-align: middle;
  transition: background 0.5s, box-shadow 0.5s;
}
.status-dot.online {
  background: #52c41a;
  box-shadow: 0 0 8px rgba(82,196,26,0.6), 0 0 20px rgba(82,196,26,0.2);
  animation: statusPulse 2s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(82,196,26,0.6); }
  50% { box-shadow: 0 0 16px rgba(82,196,26,0.8), 0 0 30px rgba(82,196,26,0.3); }
}

// ── 主内容区 ──
.main-content { flex: 1; overflow: hidden; position: relative; z-index: 2; }

// ── 底部导航 (匹配效果图底部深蓝) ──
.footer-nav {
  display: flex; justify-content: center; align-items: center;
  height: 58px; flex-shrink: 0; z-index: 100;
  background: linear-gradient(to top, rgba(1, 20, 56, 0.95) 0%, rgba(1, 20, 56, 0.35) 80%, transparent 100%);
  backdrop-filter: blur(8px);
}

.nav-inner {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 18px;
  background: rgba(4, 32, 79, 0.55);
  border: 1px solid rgba(48, 167, 209, 0.15);
  border-radius: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}

.nav-item {
  display: flex; align-items: center; gap: 5px;
  color: var(--color-text-secondary);
  font-size: 13px; cursor: pointer;
  padding: 6px 14px; border-radius: 20px;
  transition: all 0.3s ease;
  white-space: nowrap;
  position: relative;

  &:hover {
    color: var(--color-accent);
    background: rgba(48, 167, 209, 0.08);
  }
  &.active {
    color: var(--color-accent);
    background: rgba(48, 167, 209, 0.14);
    box-shadow: 0 0 12px rgba(48, 167, 209, 0.18);
  }

  &-secondary {
    font-size: 12px; padding: 5px 12px; opacity: 0.65;
    &:hover, &.active { opacity: 1; }
  }
}

.nav-separator {
  width: 1px; height: 20px;
  background: rgba(48, 167, 209, 0.15);
  margin: 0 4px;
}

// ── 过渡动画 ──
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}
.fade-enter-from { opacity: 0; transform: translateY(10px) scale(0.98); }
.fade-leave-to { opacity: 0; transform: translateY(-10px) scale(0.98); }
</style>
