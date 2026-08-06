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
  { path: '/workorders',icon: 'Tickets',         label: '智能工单' },
  { path: '/automation',icon: 'Connection',      label: '自动化集成' },
  { path: '/shift',     icon: 'Notebook',         label: '交接班' },
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

    <!-- 湖面电流特效 -->
    <svg class="lake-current" viewBox="0 0 1440 300" preserveAspectRatio="none">
      <defs>
        <filter id="glowS"><feGaussianBlur stdDeviation="1.5"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <filter id="glowM"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <filter id="glowL"><feGaussianBlur stdDeviation="6"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <linearGradient id="arcCyan" x1="0%" x2="100%">
          <stop offset="0%" stop-color="rgba(47,167,209,0)"/><stop offset="25%" stop-color="rgba(47,167,209,0.7)"/><stop offset="50%" stop-color="rgba(100,220,255,1)"/><stop offset="75%" stop-color="rgba(47,167,209,0.7)"/><stop offset="100%" stop-color="rgba(47,167,209,0)"/>
        </linearGradient>
        <linearGradient id="arcTeal" x1="0%" x2="100%">
          <stop offset="0%" stop-color="rgba(64,224,208,0)"/><stop offset="30%" stop-color="rgba(64,224,208,0.6)"/><stop offset="50%" stop-color="rgba(140,255,235,0.9)"/><stop offset="70%" stop-color="rgba(64,224,208,0.6)"/><stop offset="100%" stop-color="rgba(64,224,208,0)"/>
        </linearGradient>
        <linearGradient id="arcBlue" x1="0%" x2="100%">
          <stop offset="0%" stop-color="rgba(100,140,255,0)"/><stop offset="35%" stop-color="rgba(100,140,255,0.5)"/><stop offset="50%" stop-color="rgba(160,190,255,0.8)"/><stop offset="65%" stop-color="rgba(100,140,255,0.5)"/><stop offset="100%" stop-color="rgba(100,140,255,0)"/>
        </linearGradient>
        <radialGradient id="sparkGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="rgba(150,230,255,1)"/><stop offset="40%" stop-color="rgba(47,167,209,0.6)"/><stop offset="100%" stop-color="rgba(47,167,209,0)"/>
        </radialGradient>
      </defs>

      <!-- 电流弧线 -->
      <path d="M-50,260 Q180,160 400,200 Q620,240 800,190 Q980,140 1200,180 Q1350,195 1500,170" stroke="url(#arcCyan)" stroke-width="2.5" fill="none" stroke-dasharray="14 22" class="arc a1" filter="url(#glowM)"/>
      <path d="M-50,220 Q200,120 480,180 Q700,220 960,165 Q1150,130 1400,185 Q1450,195 1500,200" stroke="url(#arcTeal)" stroke-width="2" fill="none" stroke-dasharray="20 28" class="arc a2" filter="url(#glowM)"/>
      <path d="M-50,240 Q220,180 440,210 Q660,240 880,195 Q1080,150 1300,190 Q1410,210 1500,200" stroke="url(#arcCyan)" stroke-width="1.8" fill="none" stroke-dasharray="10 18" class="arc a3" filter="url(#glowS)"/>
      <path d="M-50,200 Q250,80 520,165 Q750,210 1000,155 Q1180,110 1440,175" stroke="url(#arcBlue)" stroke-width="1.5" fill="none" stroke-dasharray="18 30" class="arc a4" filter="url(#glowS)"/>
      <path d="M-50,280 Q180,200 380,230 Q600,260 820,215 Q1020,170 1220,210 Q1370,230 1500,220" stroke="url(#arcTeal)" stroke-width="1.2" fill="none" stroke-dasharray="8 16" class="arc a5" filter="url(#glowS)"/>
      <path d="M-50,180 Q300,60 560,150 Q800,200 1050,140 Q1250,90 1500,165" stroke="url(#arcBlue)" stroke-width="1" fill="none" stroke-dasharray="22 35" class="arc a6" filter="url(#glowS)"/>

      <!-- 光点粒子 -->
      <circle cx="280" cy="200" r="4" fill="url(#sparkGlow)" class="spark s1" filter="url(#glowS)"/>
      <circle cx="520" cy="190" r="3" fill="url(#sparkGlow)" class="spark s2" filter="url(#glowS)"/>
      <circle cx="730" cy="175" r="5" fill="url(#sparkGlow)" class="spark s3" filter="url(#glowS)"/>
      <circle cx="960" cy="185" r="3.5" fill="url(#sparkGlow)" class="spark s4" filter="url(#glowS)"/>
      <circle cx="1150" cy="195" r="4.5" fill="url(#sparkGlow)" class="spark s5" filter="url(#glowS)"/>
      <circle cx="380" cy="230" r="2.5" fill="url(#sparkGlow)" class="spark s6" filter="url(#glowS)"/>
      <circle cx="650" cy="210" r="3" fill="url(#sparkGlow)" class="spark s7" filter="url(#glowS)"/>
      <circle cx="850" cy="200" r="2" fill="url(#sparkGlow)" class="spark s8" filter="url(#glowS)"/>
      <circle cx="1080" cy="180" r="3.5" fill="url(#sparkGlow)" class="spark s9" filter="url(#glowS)"/>
      <circle cx="1350" cy="190" r="2.5" fill="url(#sparkGlow)" class="spark s10" filter="url(#glowS)"/>

      <!-- 竖线脉冲 -->
      <line x1="200" y1="285" x2="200" y2="210" stroke="rgba(47,167,209,0.15)" stroke-width="1" class="pulse p1" filter="url(#glowS)"/>
      <line x1="500" y1="280" x2="500" y2="200" stroke="rgba(47,167,209,0.12)" stroke-width="1" class="pulse p2" filter="url(#glowS)"/>
      <line x1="800" y1="275" x2="800" y2="190" stroke="rgba(64,224,208,0.12)" stroke-width="1" class="pulse p3" filter="url(#glowS)"/>
      <line x1="1100" y1="282" x2="1100" y2="195" stroke="rgba(47,167,209,0.15)" stroke-width="1" class="pulse p4" filter="url(#glowS)"/>
      <line x1="1350" y1="280" x2="1350" y2="205" stroke="rgba(64,224,208,0.1)" stroke-width="1" class="pulse p5" filter="url(#glowS)"/>
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
    <div class="disclaimer-bar">
      ⚠️ 本系统诊断结果为 AI 辅助分析，仅供参考。任何涉及设备停运、并网解列的操作决策，必须经值长或专工人工确认后执行。
    </div>
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  display: flex; flex-direction: column; height: 100vh; overflow: hidden;
  position: relative; z-index: 1;
}

.effect-bg {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
  background-image: url('/effect-bg.png');
  background-size: cover; background-position: center; background-repeat: no-repeat;
}

// ── 湖面电流特效 (底部30%) ──
.lake-current {
  position: fixed; bottom: 6%; left: 0; width: 100%; height: 28%;
  z-index: 0; pointer-events: none; opacity: 0.85;
}

.arc { animation: currentDrift 4s linear infinite; }
.a1 { animation-duration: 4s; }
.a2 { animation-duration: 5.5s; animation-delay: 0.8s; }
.a3 { animation-duration: 3.5s; animation-delay: 1.5s; }
.a4 { animation-duration: 6s; animation-delay: 0.3s; }
.a5 { animation-duration: 3s; animation-delay: 2s; }
.a6 { animation-duration: 7s; animation-delay: 1s; }

@keyframes currentDrift {
  0% { stroke-dashoffset: 0; opacity: 0.2; }
  25% { opacity: 1; }
  50% { opacity: 0.6; }
  75% { opacity: 0.9; }
  100% { stroke-dashoffset: -100; opacity: 0.2; }
}

.spark { animation: sparkFloat 3s ease-in-out infinite; }
.s1 { animation-delay: 0s; animation-duration: 2.8s; }
.s2 { animation-delay: 0.4s; animation-duration: 3.2s; }
.s3 { animation-delay: 0.8s; animation-duration: 2.5s; }
.s4 { animation-delay: 1.2s; animation-duration: 3.5s; }
.s5 { animation-delay: 1.6s; animation-duration: 2.7s; }
.s6 { animation-delay: 0.2s; animation-duration: 3.8s; }
.s7 { animation-delay: 0.7s; animation-duration: 2.9s; }
.s8 { animation-delay: 1.0s; animation-duration: 3.1s; }
.s9 { animation-delay: 1.5s; animation-duration: 2.6s; }
.s10 { animation-delay: 1.9s; animation-duration: 3.4s; }

@keyframes sparkFloat {
  0%, 100% { opacity: 0.1; transform: scale(0.3) translateY(0); }
  20% { opacity: 1; transform: scale(1.4) translateY(-8px); }
  40% { opacity: 0.6; transform: scale(0.8) translateY(-4px); }
  60% { opacity: 0.9; transform: scale(1.2) translateY(-10px); }
  80% { opacity: 0.3; transform: scale(0.6) translateY(-2px); }
}

.pulse { animation: pulseLine 4s ease-in-out infinite; }
.p1 { animation-delay: 0s; }
.p2 { animation-delay: 1s; }
.p3 { animation-delay: 2s; }
.p4 { animation-delay: 0.5s; }
.p5 { animation-delay: 1.5s; }

@keyframes pulseLine {
  0%, 100% { opacity: 0.05; }
  25% { opacity: 0.5; }
  50% { opacity: 0.15; }
  75% { opacity: 0.4; }
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

.disclaimer-bar {
  flex-shrink: 0; z-index: 100;
  text-align: center; padding: 4px 16px;
  font-size: 12px; color: rgba(232,136,85,0.8);
  background: rgba(232,85,85,0.06);
  border-top: 1px solid rgba(232,85,85,0.12);
}

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
