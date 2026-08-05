<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const time = ref(new Date())

onMounted(() => {
  setInterval(() => { time.value = new Date() }, 1000)
  if (auth.isLoggedIn) router.replace('/')
})

async function login() {
  if (!username.value.trim() || !password.value.trim()) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  await new Promise(r => setTimeout(r, 800))
  if (username.value === 'admin' && password.value === 'yuneng2024') {
    auth.login(username.value)
    router.replace('/')
  } else {
    error.value = '用户名或密码错误'
    loading.value = false
  }
}
</script>

<template>
  <div class="login-root">
    <div class="login-bg"></div>

    <!-- 湖面电流 -->
    <svg class="lake-current" viewBox="0 0 1440 300" preserveAspectRatio="none">
      <defs>
        <filter id="lg"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <linearGradient id="la1" x1="0%" x2="100%">
          <stop offset="0%" stop-color="rgba(47,167,209,0)"/><stop offset="30%" stop-color="rgba(47,167,209,0.9)"/><stop offset="50%" stop-color="rgba(100,220,255,1)"/><stop offset="70%" stop-color="rgba(47,167,209,0.9)"/><stop offset="100%" stop-color="rgba(47,167,209,0)"/>
        </linearGradient>
        <linearGradient id="la2" x1="0%" x2="100%">
          <stop offset="0%" stop-color="rgba(64,224,208,0)"/><stop offset="35%" stop-color="rgba(64,224,208,0.8)"/><stop offset="50%" stop-color="rgba(160,255,240,0.9)"/><stop offset="65%" stop-color="rgba(64,224,208,0.8)"/><stop offset="100%" stop-color="rgba(64,224,208,0)"/>
        </linearGradient>
      </defs>
      <path d="M0,240 Q200,170 400,200 Q600,230 800,190 Q1000,150 1200,180 Q1350,200 1440,170" stroke="url(#la1)" stroke-width="2.2" fill="none" stroke-dasharray="16 24" class="larc l1" filter="url(#lg)"/>
      <path d="M0,220 Q250,140 500,180 Q750,220 1000,170 Q1200,130 1440,190" stroke="url(#la2)" stroke-width="1.5" fill="none" stroke-dasharray="24 32" class="larc l2" filter="url(#lg)"/>
      <path d="M100,260 Q350,190 600,230 Q850,270 1100,220 Q1300,190 1440,240" stroke="url(#la1)" stroke-width="2.4" fill="none" stroke-dasharray="12 20" class="larc l3" filter="url(#lg)"/>
    </svg>

    <div class="login-card">
      <div class="lc-top">
        <div class="lc-logo">⚡</div>
        <h1 class="lc-title">驭能智能诊断平台</h1>
        <p class="lc-sub">新能源场站非计划停机智能诊断系统</p>
      </div>

      <form class="lc-form" @submit.prevent="login">
        <div class="lc-field">
          <label>用户名</label>
          <el-input v-model="username" placeholder="请输入用户名" size="large" :disabled="loading" clearable>
            <template #prefix><el-icon><component is="User" /></el-icon></template>
          </el-input>
        </div>

        <div class="lc-field">
          <label>密码</label>
          <el-input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="请输入密码" size="large" :disabled="loading" show-password>
            <template #prefix><el-icon><component is="Lock" /></el-icon></template>
          </el-input>
        </div>

        <div v-if="error" class="lc-error">{{ error }}</div>

        <el-button type="primary" size="large" native-type="submit" :loading="loading" class="lc-btn">
          {{ loading ? '验证中...' : '登 录' }}
        </el-button>
      </form>

      <div class="lc-footer">
        <span class="lc-time font-digital">{{ time.toLocaleTimeString('zh-CN', { hour12: false }) }}</span>
        <span class="lc-sep">|</span>
        <span>DeepSeek V4 Pro · 8 Agent</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-root {
  height: 100vh; display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
}
.login-bg {
  position: fixed; inset: 0; z-index: 0;
  background: url('/effect-bg.jpg') center/cover no-repeat;
}

// 湖面电流
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

.login-card {
  position: relative; z-index: 2;
  width: 420px; padding: 40px 36px 28px;
  background: rgba(4, 24, 56, 0.55);
  border: 1px solid rgba(47, 167, 209, 0.18);
  border-radius: 14px;
  backdrop-filter: blur(16px);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(47,167,209,0.06) inset;
}

.lc-top { text-align: center; margin-bottom: 28px; }
.lc-logo {
  font-size: 44px; margin-bottom: 8px;
  filter: drop-shadow(0 0 12px rgba(48, 167, 209, 0.5));
  animation: logoPulse 2s ease-in-out infinite;
}
@keyframes logoPulse {
  0%,100% { filter: drop-shadow(0 0 12px rgba(48,167,209,0.5)); }
  50% { filter: drop-shadow(0 0 22px rgba(48,167,209,0.85)); }
}
.lc-title {
  font-size: 26px; font-weight: 700; letter-spacing: 5px; margin: 0 0 6px;
  background: linear-gradient(180deg, #E8ECF1 0%, #8EC8E0 50%, #3A90C0 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 12px rgba(48, 167, 209, 0.4));
}
.lc-sub { font-size: 12px; color: #6a88a8; letter-spacing: 1px; }

.lc-form { display: flex; flex-direction: column; gap: 16px; }
.lc-field label { display: block; font-size: 12px; color: #8ba0c8; margin-bottom: 6px; letter-spacing: 0.5px; }
.lc-error { font-size: 13px; color: #E85555; text-align: center; padding: 4px 0; }
.lc-btn {
  width: 100%; margin-top: 4px; height: 44px; font-size: 15px; letter-spacing: 4px;
  background: linear-gradient(135deg, rgba(47,167,209,0.3), rgba(47,167,209,0.12)) !important;
  border-color: rgba(47,167,209,0.4) !important;
  &:hover { background: linear-gradient(135deg, rgba(47,167,209,0.45), rgba(47,167,209,0.2)) !important; }
}

.lc-footer {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  margin-top: 20px; font-size: 11px; color: #5a78a0;
  .lc-time { font-size: 14px; color: #8ba0c8; letter-spacing: 1px; }
  .lc-sep { color: rgba(47,167,209,0.2); }
}
</style>
