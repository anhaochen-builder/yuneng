<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { healthCheck } from './api'
import { useAuthStore } from './stores/auth'
import AlarmAlertOverlay from './components/AlarmAlertOverlay.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const systemReady = ref(false)
const now = ref(new Date())
const uptime = ref('00:00:00')
let clockTimer: ReturnType<typeof setInterval> | null = null
let startTime = Date.now()

onMounted(async () => {
  try { await healthCheck(); systemReady.value = true } catch { systemReady.value = true }
  clockTimer = setInterval(() => { now.value = new Date() }, 1000)
})

onUnmounted(() => { if (clockTimer) clearInterval(clockTimer) })

const uptimeStr = computed(() => {
  const elapsed = Math.floor((Date.now() - startTime) / 1000)
  const h = Math.floor(elapsed / 3600).toString().padStart(2, '0')
  const m = Math.floor((elapsed % 3600) / 60).toString().padStart(2, '0')
  const s = (elapsed % 60).toString().padStart(2, '0')
  return `${h}:${m}:${s}`
})

const navItems = [
  { path: '/',          icon: 'Odometer',        label: '总览看板' },
  { path: '/diagnostic', icon: 'ChatDotRound',   label: '智能诊断' },
  { path: '/scada',     icon: 'Monitor',         label: 'SCADA看板' },
  { path: '/alarms',    icon: 'Bell',            label: '告警管理' },
  { path: '/monitor',   icon: 'DataAnalysis',    label: '设备监控' },
  { path: '/reports',   icon: 'Document',        label: '报表管理' },
  { path: '/knowledge', icon: 'Collection',      label: '知识库' },
  { path: '/devices',   icon: 'Cpu',             label: '设备管理' },
  { path: '/settings',  icon: 'Setting',         label: '系统设置' },
]

function go(path: string) { router.push(path) }
function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function clockTicker() {
  now.value = new Date()
  uptime.value = uptimeStr.value
  requestAnimationFrame(clockTicker)
}
onMounted(() => requestAnimationFrame(clockTicker))
</script>

<template>
  <div class="app-shell">
    <div class="effect-bg"></div>

    <!-- 湖面电流特效 (全局背景层底部) -->
    <svg class="lake-current" viewBox="0 0 1440 300" preserveAspectRatio="none">
      <defs>
        <filter id="lakeGlow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <linearGradient id="lakeArc1" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(47,167,209,0)"/><stop offset="30%" stop-color="rgba(47,167,209,0.9)"/><stop offset="50%" stop-color="rgba(100,220,255,1)"/><stop offset="70%" stop-color="rgba(47,167,209,0.9)"/><stop offset="100%" stop-color="rgba(47,167,209,0)"/>
        </linearGradient>
        <linearGradient id="lakeArc2" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(64,224,208,0)"/><stop offset="35%" stop-color="rgba(64,224,208,0.8)"/><stop offset="50%" stop-color="rgba(160,255,240,0.9)"/><stop offset="65%" stop-color="rgba(64,224,208,0.8)"/><stop offset="100%" stop-color="rgba(64,224,208,0)"/>
        </linearGradient>
      </defs>
      <path d="M0,250 Q200,180 400,210 Q600,240 800,200 Q1000,160 1200,190 Q1350,210 1440,180" stroke="url(#lakeArc1)" stroke-width="2" fill="none" stroke-dasharray="16 24" class="larc l1" filter="url(#lakeGlow)"/>
      <path d="M0,230 Q250,150 500,190 Q750,230 1000,180 Q1200,140 1440,200" stroke="url(#lakeArc2)" stroke-width="1.5" fill="none" stroke-dasharray="24 32" class="larc l2" filter="url(#lakeGlow)"/>
      <path d="M100,270 Q350,200 600,240 Q850,280 1100,230 Q1300,200 1440,250" stroke="url(#lakeArc1)" stroke-width="2.2" fill="none" stroke-dasharray="12 20" class="larc l3" filter="url(#lakeGlow)"/>
      <circle cx="350" cy="215" r="3" fill="rgba(100,220,255,0.8)" class="lspark lsp1" filter="url(#lakeGlow)"/>
      <circle cx="800" cy="195" r="2.5" fill="rgba(64,224,208,0.8)" class="lspark lsp2" filter="url(#lakeGlow)"/>
      <circle cx="1100" cy="225" r="2" fill="rgba(100,220,255,0.7)" class="lspark lsp3" filter="url(#lakeGlow)"/>
    </svg>

    <AlarmAlertOverlay />

    <!-- 顶部栏 -->
    <header class="dashboard-header">
      <!-- 顶部扫描线 -->
      <div class="header-scan-line"></div>

      <div class="header-inner">
        <!-- 左侧: 系统信息 -->
        <div class="header-left">
          <div class="logo-block">
            <span class="logo-glow">⚡</span>
            <div class="logo-text-group">
              <span class="logo-text">YUNENG</span>
              <span class="logo-sub">Smart Diagnosis</span>
            </div>
          </div>
          <span class="header-sep"></span>
          <div class="status-group">
            <span class="status-dot" :class="{ online: systemReady }"></span>
            <div class="status-text-group">
              <span class="status-label">{{ systemReady ? 'ONLINE' : 'CONNECTING' }}</span>
              <span class="status-uptime">UPTIME {{ uptime }}</span>
            </div>
          </div>
          <span class="header-sep"></span>
          <span class="model-tag">DS V4 PRO</span>
        </div>

        <!-- 中间: 标题 -->
        <div class="header-center">
          <h1 class="header-title">
            <span class="title-deco left"></span>
            <span class="title-content">驭能智能诊断平台</span>
            <span class="title-deco right"></span>
          </h1>
          <div class="title-underline"></div>
        </div>

        <!-- 右侧: 时间 + 快捷 -->
        <div class="header-right">
          <div class="datetime-group">
            <span class="header-date">{{ now.toLocaleDateString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit', weekday:'short' }) }}</span>
            <span class="header-time font-digital">{{ now.toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
          </div>
          <span class="header-sep"></span>
          <el-button class="settings-btn" @click="go('/settings')">
            <el-icon :size="18"><component is="Setting" /></el-icon>
          </el-button>
          <el-button class="logout-btn" @click="auth.logout(); router.replace('/login')">
            <el-icon :size="16"><component is="SwitchButton" /></el-icon>
          </el-button>
        </div>
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

    <!-- 底部导航 -->
    <footer class="footer-nav">
      <div class="nav-inner">
        <div
          v-for="item in navItems" :key="item.path"
          class="nav-item" :class="{ active: isActive(item.path) }"
          @click="go(item.path)"
        >
          <el-icon :size="17"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
          <span v-if="isActive(item.path)" class="nav-active-dot"></span>
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

.effect-bg {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
  background-image: url('/effect-bg.jpg');
  background-size: cover; background-position: center; background-repeat: no-repeat;
}

// ── 湖面电流特效 (底部30%) ──
.lake-current {
  position: fixed; bottom: 8%; left: 0; width: 100%; height: 30%;
  z-index: 0; pointer-events: none; opacity: 0.7;
}
.larc {
  animation: currentDrift 5s linear infinite;
  &.l1 { animation-duration: 5s; }
  &.l2 { animation-duration: 6.5s; animation-delay: 1.5s; }
  &.l3 { animation-duration: 4s; animation-delay: 0.8s; }
}
@keyframes currentDrift {
  0% { stroke-dashoffset: 0; opacity: 0.3; }
  40% { opacity: 1; }
  70% { opacity: 0.8; }
  100% { stroke-dashoffset: -80; opacity: 0.3; }
}
.lspark {
  animation: lakeSpark 3s ease-in-out infinite;
  &.lsp1 { animation-delay: 0s; }
  &.lsp2 { animation-delay: 1.5s; }
  &.lsp3 { animation-delay: 2.2s; }
}
@keyframes lakeSpark {
  0%,100% { opacity: 0.1; transform: scale(0.5); }
  25% { opacity: 1; transform: scale(1.5); }
  50% { opacity: 0.3; transform: scale(0.8); }
  75% { opacity: 0.9; transform: scale(1.3); }
}

// ── 顶部栏 ──
.dashboard-header {
  flex-shrink: 0; z-index: 100;
  position: relative;
  background: linear-gradient(180deg,
    rgba(2, 18, 48, 0.95) 0%,
    rgba(4, 28, 64, 0.85) 60%,
    rgba(4, 32, 72, 0.5) 100%
  );
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(48, 167, 209, 0.12);
}

.header-scan-line {
  position: absolute; bottom: 0; left: 10%; width: 80%; height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(48, 167, 209, 0) 30%,
    rgba(48, 167, 209, 0.6) 50%,
    rgba(48, 167, 209, 0) 70%,
    transparent 100%
  );
  animation: scan 4s ease-in-out infinite;
}
@keyframes scan {
  0%, 100% { opacity: 0.3; left: 5%; width: 90%; }
  50% { opacity: 1; left: 15%; width: 70%; }
}

.header-inner {
  display: flex; align-items: center;
  height: 72px; padding: 0 28px;
  max-width: 1920px; margin: 0 auto;
}

// ── 左侧 ──
.header-left {
  display: flex; align-items: center; gap: 14px; z-index: 1; min-width: 360px;
}
.logo-block {
  display: flex; align-items: center; gap: 10px;
}
.logo-glow {
  font-size: 26px;
  filter: drop-shadow(0 0 8px rgba(48, 167, 209, 0.6));
  animation: logoPulse 2s ease-in-out infinite;
}
@keyframes logoPulse {
  0%,100% { filter: drop-shadow(0 0 8px rgba(48, 167, 209, 0.6)); }
  50% { filter: drop-shadow(0 0 18px rgba(48, 167, 209, 0.9)); }
}
.logo-text-group { display: flex; flex-direction: column; line-height: 1.15; }
.logo-text {
  font-family: 'Orbitron', monospace;
  font-size: 14px; font-weight: 700; letter-spacing: 3px;
  color: #fff;
  text-shadow: 0 0 10px rgba(48, 167, 209, 0.3);
}
.logo-sub {
  font-size: 9px; color: var(--color-accent); letter-spacing: 1.5px;
  opacity: 0.65;
}

.header-sep {
  width: 1px; height: 28px;
  background: linear-gradient(180deg, transparent, rgba(48,167,209,0.3), transparent);
}

.status-group { display: flex; align-items: center; gap: 8px; }
.status-dot {
  width: 9px; height: 9px; border-radius: 50%;
  background: #ff4d4f; flex-shrink: 0;
  transition: all 0.5s;
  box-shadow: 0 0 6px rgba(255,77,79,0.4);
}
.status-dot.online {
  background: #52c41a;
  box-shadow: 0 0 8px rgba(82,196,26,0.6), 0 0 16px rgba(82,196,26,0.2);
  animation: statusPulse 2s ease-in-out infinite;
}
@keyframes statusPulse {
  0%,100% { box-shadow: 0 0 8px rgba(82,196,26,0.6); }
  50% { box-shadow: 0 0 16px rgba(82,196,26,0.8), 0 0 24px rgba(82,196,26,0.3); }
}
.status-text-group { display: flex; flex-direction: column; line-height: 1.2; }
.status-label { font-size: 11px; color: var(--color-text-secondary); letter-spacing: 1px; text-transform: uppercase; }
.status-uptime { font-size: 9px; color: var(--color-text-secondary); opacity: 0.55; letter-spacing: 0.5px; }

.model-tag {
  padding: 3px 10px; font-size: 10px; font-weight: 700;
  letter-spacing: 1.5px;
  color: var(--color-accent);
  background: rgba(48, 167, 209, 0.12);
  border: 1px solid rgba(48, 167, 209, 0.25);
  border-radius: 3px;
  font-family: 'Orbitron', monospace;
}

// ── 中间标题 ──
.header-center {
  position: absolute; left: 50%; transform: translateX(-50%);
  z-index: 2; text-align: center;
}
.header-title {
  font-size: 28px; font-weight: 700; letter-spacing: 6px;
  white-space: nowrap;
  display: flex; align-items: center; gap: 0;
  margin: 0;
}
.title-deco {
  display: inline-block; width: 60px; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(48,167,209,0.5));
  vertical-align: middle;
  &.left { background: linear-gradient(90deg, transparent, rgba(48,167,209,0.5)); }
  &.right { background: linear-gradient(90deg, rgba(48,167,209,0.5), transparent); }
}
.title-content {
  background: linear-gradient(180deg, #E8ECF1 0%, #8EC8E0 45%, #3A90C0 75%, #1A6280 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 14px rgba(48, 167, 209, 0.5));
  padding: 0 16px;
}
.title-underline {
  width: 180px; height: 1px; margin: 4px auto 0;
  background: linear-gradient(90deg, transparent, rgba(48,167,209,0.4) 20%, rgba(255,255,255,0.6) 50%, rgba(48,167,209,0.4) 80%, transparent);
}

// ── 右侧 ──
.header-right {
  display: flex; align-items: center; gap: 14px; z-index: 1;
  margin-left: auto;
}
.datetime-group { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.2; }
.header-date { font-size: 12px; color: var(--color-text-secondary); letter-spacing: 0.5px; }
.header-time {
  font-size: 22px; font-weight: bold; color: #fff;
  letter-spacing: 1.5px;
  text-shadow: 0 0 12px rgba(48, 167, 209, 0.3);
}
.settings-btn, .logout-btn {
  width: 36px; height: 36px;
  background: rgba(48, 167, 209, 0.08) !important;
  border: 1px solid rgba(48, 167, 209, 0.2) !important;
  color: var(--color-accent) !important;
  transition: all 0.18s;
  &:hover {
    background: rgba(48, 167, 209, 0.18) !important;
    border-color: var(--color-accent) !important;
  }
}
.settings-btn:hover { transform: rotate(30deg); }
.logout-btn:hover { color: #E85555 !important; border-color: rgba(232,85,85,0.35) !important; }

// ── 主内容区 ──
.main-content { flex: 1; overflow: hidden; position: relative; z-index: 2; }

// ── 底部导航 ──
.footer-nav {
  display: flex; justify-content: center; align-items: center;
  height: 60px; flex-shrink: 0; z-index: 100;
  background: linear-gradient(to top,
    rgba(2, 18, 48, 0.97) 0%,
    rgba(2, 18, 48, 0.4) 80%,
    transparent 100%
  );
  backdrop-filter: blur(8px);
}
.nav-inner {
  display: flex; align-items: center; gap: 2px;
  padding: 5px 20px;
  background: linear-gradient(180deg, rgba(6,36,80,0.5), rgba(4,26,62,0.6));
  border: 1px solid rgba(48, 167, 209, 0.12);
  border-radius: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(48,167,209,0.06);
}
.nav-item {
  display: flex; align-items: center; gap: 5px;
  color: var(--color-text-secondary);
  font-size: 13px; cursor: pointer;
  padding: 6px 16px; border-radius: 20px;
  transition: all 0.18s ease;
  &:hover {
    color: var(--color-accent);
    background: rgba(48, 167, 209, 0.08);
  }
  &.active {
    color: #fff;
    background: rgba(48, 167, 209, 0.15);
    box-shadow: 0 0 12px rgba(48, 167, 209, 0.2);
  }
}
.nav-active-dot {
  position: absolute; bottom: 3px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px; border-radius: 50%;
  background: var(--color-accent);
  box-shadow: 0 0 6px var(--color-accent);
}

// ── 过渡动画 ──
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-enter-from { opacity: 0; transform: translateY(4px) scale(0.99); }
.fade-leave-to { opacity: 0; transform: translateY(-4px) scale(0.99); }
</style>
