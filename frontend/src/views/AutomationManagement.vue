<template>
  <div class="auto-page">
    <div class="grid-2col">
      <!-- 设备发现 -->
      <div class="tech-card">
        <h4>🔍 设备自动发现</h4>
        <div class="discovery-actions">
          <el-button size="small" type="primary" :loading="discovering" @click="runDiscovery(false)">本地扫描</el-button>
          <el-button size="small" :loading="discovering" @click="runDiscovery(true)">网络扫描</el-button>
          <el-button size="small" :loading="connecting" @click="autoConnect">自动连接</el-button>
        </div>
        <div v-if="discoveryResult" class="discovery-result">
          <span class="dr-note">{{ discoveryResult.note }}</span>
          <div v-if="discoveryResult.local?.length" class="device-list">
            <div v-for="d in discoveryResult.local" :key="d.device_id" class="device-row">
              <span class="d-id">{{ d.device_id }}</span>
              <span class="d-host">{{ d.host }}:{{ d.port }}</span>
              <el-tag size="small" type="info">{{ d.protocol }}</el-tag>
              <span class="d-status">{{ d.status }}</span>
            </div>
          </div>
          <div v-if="discoveryResult.network?.length" class="device-list">
            <div v-for="d in discoveryResult.network" :key="d.device_id" class="device-row">
              <span class="d-id">{{ d.device_id }}</span>
              <span class="d-host">{{ d.host }}:{{ d.port }}</span>
              <el-tag size="small" type="info">{{ d.protocol }}</el-tag>
              <span class="d-status">{{ d.status }}</span>
            </div>
          </div>
          <div v-if="!discoveryResult.local?.length && !discoveryResult.network?.length" class="empty-note">
            未发现设备，请确保 SCADA 设备在同一网络
          </div>
        </div>
      </div>

      <!-- 外部告警接入 -->
      <div class="tech-card">
        <h4>📡 告警自动接入</h4>
        <div class="webhook-info">
          <div class="wh-row"><span>Webhook 地址</span><code>POST /api/external/webhook/alarm</code></div>
          <div class="wh-row"><span>测试示例</span><el-button size="small" text @click="testWebhook">发送测试</el-button></div>
        </div>
        <div class="code-block">
          <pre>curl -X POST http://localhost:8080/api/external/webhook/alarm \
  -H "Content-Type: application/json" \
  -d '{"device_id":"INV001","alarm_type":"过热","alarm_level":"HIGH","alarm_message":"IGBT温度98°C超阈值"}'</pre>
        </div>
        <div v-if="webhookResult" class="wh-result" :class="webhookResult.startsWith('✅') ? 'ok' : 'err'">{{ webhookResult }}</div>
      </div>
    </div>

    <!-- 通知推送配置 -->
    <div class="tech-card">
      <h4>📬 自动通知推送</h4>
      <div class="notify-form">
        <div class="nf-row">
          <label>启用定时巡检</label>
          <el-switch v-model="notifyConfig.enabled" />
          <span class="nf-hint">每日 {{ notifyConfig.schedule_time }} 自动诊断 6 类核心设备</span>
        </div>
        <div class="nf-row">
          <label>巡检时间</label>
          <el-input v-model="notifyConfig.schedule_time" size="small" style="width:120px" placeholder="08:00" />
        </div>
        <div class="nf-row">
          <label>钉钉 Webhook</label>
          <el-input v-model="notifyConfig.dingtalk_webhook" size="small" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
        </div>
        <div class="nf-row">
          <label>企业微信 Webhook</label>
          <el-input v-model="notifyConfig.wecom_webhook" size="small" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
        </div>
        <div class="nf-actions">
          <el-button type="primary" size="small" :loading="notifySaving" @click="saveNotify">保存配置</el-button>
          <el-button size="small" :loading="notifyTesting" @click="testNotify">测试推送</el-button>
          <el-button size="small" @click="runDailyReport">立即巡检</el-button>
        </div>
        <div v-if="notifyResult" class="nf-result">{{ notifyResult }}</div>
      </div>
    </div>

    <!-- 最近外部告警 -->
    <div class="tech-card">
      <h4>📋 最近外部告警</h4>
      <el-table :data="externalAlarms" size="small" v-if="externalAlarms.length">
        <el-table-column prop="alarm_id" label="告警ID" width="160" />
        <el-table-column prop="device_id" label="设备" width="100" />
        <el-table-column prop="alarm_level" label="级别" width="80">
          <template #default="{ row: r }"><el-tag size="small" :type="r.alarm_level==='CRITICAL'?'danger':r.alarm_level==='HIGH'?'warning':'info'">{{ r.alarm_level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="alarm_message" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="received_at" label="时间" width="160" />
      </el-table>
      <div v-else class="empty-note">暂无外部告警，可通过 Webhook 推送测试</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

const discovering = ref(false)
const connecting = ref(false)
const discoveryResult = ref<any>(null)
const webhookResult = ref('')
const externalAlarms = ref<any[]>([])
const notifyConfig = ref({
  enabled: false, schedule_time: '08:00', dingtalk_webhook: '', wecom_webhook: '',
  email_smtp_host: '', email_smtp_port: 465, email_user: '', email_password: '', email_receivers: [] as string[],
})
const notifySaving = ref(false)
const notifyTesting = ref(false)
const notifyResult = ref('')

onMounted(async () => {
  try {
    const r = await api.get('/api/external/alarms')
    externalAlarms.value = (r.data as any)?.data?.alarms || (r.data as any)?.alarms || []
  } catch {}
  try {
    const r = await api.get('/api/automation/notify/config')
    Object.assign(notifyConfig.value, (r.data as any)?.data || r.data)
  } catch {}
})

async function runDiscovery(scan: boolean) {
  discovering.value = true
  try {
    const r = await api.get(`/api/automation/discovery?scan_network=${scan}`)
    discoveryResult.value = (r.data as any)?.data || r.data
  } catch {}
  discovering.value = false
}

async function autoConnect() {
  connecting.value = true
  try { await api.post('/api/automation/discovery/auto-connect') } catch {}
  connecting.value = false
}

async function testWebhook() {
  try {
    await api.post('/api/external/webhook/alarm', {
      device_id: 'INV001', alarm_type: '测试', alarm_level: 'MEDIUM',
      alarm_message: '这是一条来自平台的测试告警', auto_diagnose: false,
    })
    webhookResult.value = '✅ 测试告警已发送'
    const r = await api.get('/api/external/alarms')
    externalAlarms.value = (r.data as any)?.data?.alarms || []
  } catch { webhookResult.value = '❌ 发送失败' }
}

async function saveNotify() {
  notifySaving.value = true
  try { await api.post('/api/automation/notify/config', notifyConfig.value) } catch {}
  notifySaving.value = false
  notifyResult.value = '✅ 已保存'
  setTimeout(() => { notifyResult.value = '' }, 3000)
}

async function testNotify() {
  notifyTesting.value = true
  try {
    const r = await api.post('/api/automation/notify/test', notifyConfig.value)
    const data = (r.data as any)?.data || r.data
    notifyResult.value = `钉钉: ${data?.results?.dingtalk || '未配置'} | 企微: ${data?.results?.wecom || '未配置'}`
  } catch { notifyResult.value = '❌ 测试失败' }
  notifyTesting.value = false
}

async function runDailyReport() {
  try {
    await api.post('/api/automation/notify/run-now')
    notifyResult.value = '✅ 巡检任务已启动'
  } catch { notifyResult.value = '❌ 启动失败' }
}
</script>

<style scoped>
.auto-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
h4 { color: var(--color-accent); margin: 0 0 12px; font-size: 14px; }
.discovery-actions { display: flex; gap: 8px; margin-bottom: 12px; }
.discovery-result { font-size: 13px; }
.dr-note { display: block; color: var(--color-text-secondary); margin-bottom: 8px; }
.device-list { margin-bottom: 8px; }
.device-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.06); }
.d-id { color: var(--color-accent); font-family: monospace; min-width: 120px; }
.d-host { color: var(--color-text-secondary); font-size: 12px; }
.d-status { color: #52c41a; font-size: 12px; }
.webhook-info { margin-bottom: 10px; }
.wh-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; color: var(--color-text-secondary); font-size: 13px; }
.wh-row code { color: var(--color-accent); font-family: monospace; font-size: 12px; }
.code-block { background: rgba(0,0,0,0.3); border-radius: 4px; padding: 10px; margin-bottom: 10px; overflow-x: auto; }
.code-block pre { color: #52c41a; font-size: 11px; margin: 0; white-space: pre-wrap; }
.wh-result { font-size: 13px; padding: 4px 0; }
.wh-result.ok { color: #52c41a; }
.wh-result.err { color: #ff4d4f; }

.notify-form { display: flex; flex-direction: column; gap: 10px; }
.nf-row { display: flex; align-items: center; gap: 10px; }
.nf-row label { width: 120px; color: var(--color-text-secondary); font-size: 13px; }
.nf-row .el-input { flex: 1; }
.nf-hint { color: var(--color-text-secondary); font-size: 12px; }
.nf-actions { display: flex; gap: 8px; }
.nf-result { font-size: 13px; color: #52c41a; }
.empty-note { text-align: center; color: var(--color-text-secondary); font-size: 13px; padding: 20px; }
</style>
