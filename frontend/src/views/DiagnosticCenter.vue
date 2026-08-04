<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSSE } from '@/hooks/useSSE'
import { feedbackApi } from '@/api'

const route = useRoute()
const { isStreaming, currentStep, streamedContent, diagnosisReport, error, sendMessage, abort } = useSSE()
const inputText = ref('')
const chatMessages = ref<Array<{ role: string; content: string; timestamp: string }>>([])
const messagesEnd = ref<HTMLElement | null>(null)
const feedbackGiven = ref(false)
const feedbackResult = ref('')

const quickActions = [
  '3号逆变器通讯中断，后台报ALM-001',
  '1号风机齿轮箱油温超过80°C，振动值升高',
  '变压器油温异常，当前85°C，DGA氢气超标',
  '光伏逆变器直流侧绝缘阻抗降低至300kΩ',
]

function scrollBottom() { nextTick(() => messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })) }

async function send() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return
  chatMessages.value.push({ role: 'user', content: text, timestamp: new Date().toLocaleTimeString() })
  inputText.value = ''
  feedbackGiven.value = false
  await scrollBottom()

  const apiBase = import.meta.env.VITE_API_BASE_URL || ''
  await sendMessage(`${apiBase}/api/diagnose/stream`, { symptoms: text })
  const content = streamedContent.value || '诊断完成'
  chatMessages.value.push({ role: 'assistant', content, timestamp: new Date().toLocaleTimeString() })
  await scrollBottom()
}

function useQuick(text: string) { inputText.value = text; send() }

async function submitFeedback(rating: string) {
  if (!diagnosisReport.value) return
  try {
    await feedbackApi.submit(diagnosisReport.value.task_id || 'unknown', rating)
    feedbackGiven.value = true
    feedbackResult.value = rating === 'accurate' ? '感谢反馈！案例已入库' : '感谢反馈，已记录'
  } catch { feedbackResult.value = '反馈提交失败' }
}

const q = route.query.q as string
if (q) { inputText.value = q; setTimeout(send, 500) }
</script>

<template>
  <div class="diagnostic-page animate-fade-in">
    <div class="chat-panel tech-card">
      <div class="chat-messages">
        <div v-for="(msg, i) in chatMessages" :key="i" :class="['msg', msg.role]">
          <div class="msg-content" v-html="msg.content.replace(/\n/g, '<br>')"></div>
          <div class="msg-time">{{ msg.timestamp }}</div>
        </div>
        <div v-if="isStreaming" class="msg assistant">
          <div class="streaming">
            <span class="typing-dots"><span></span><span></span><span></span></span>
            <span class="step-text">{{ currentStep || '诊断中...' }}</span>
          </div>
          <div class="stream-preview">{{ streamedContent }}</div>
        </div>
        <div ref="messagesEnd"></div>
      </div>
      <div class="quick-actions">
        <el-button v-for="act in quickActions" :key="act" size="small" text @click="useQuick(act)" :disabled="isStreaming">{{ act.slice(0, 40) }}...</el-button>
      </div>
      <div class="input-row">
        <el-input v-model="inputText" placeholder="描述故障现象..." @keyup.enter="send" :disabled="isStreaming" size="large">
          <template #append>
            <el-button @click="send" :disabled="isStreaming || !inputText.trim()" type="primary" :icon="isStreaming ? 'Loading' : 'Promotion'">
              {{ isStreaming ? '诊断中' : '发送' }}
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div class="report-sidebar" v-if="diagnosisReport">
      <div class="tech-card report-card">
        <h4>🔧 诊断报告</h4>
        <div v-if="diagnosisReport.root_causes?.length" class="section">
          <div class="section-title">可能原因</div>
          <div v-for="(c, i) in diagnosisReport.root_causes" :key="i" class="cause-row">
            <span class="cause-rank">#{{ Number(i) + 1 }}</span>
            <span class="cause-text">{{ c.cause }}</span>
            <span class="cause-prob" :style="{ color: c.probability > 0.7 ? '#ff4d4f' : c.probability > 0.4 ? '#ff9c40' : '#52c41a' }">{{ ((Number(c.probability) || 0) * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div class="section">
          <div class="section-title">置信度</div>
          <el-progress :percentage="(Number(diagnosisReport.confidence) || 0) * 100" :color="(p: number) => p > 70 ? '#52c41a' : p > 40 ? '#ff9c40' : '#ff4d4f'" />
        </div>
        <div v-if="diagnosisReport.risk_level" class="section">
          <div class="section-title">风险等级</div>
          <el-tag :type="diagnosisReport.risk_level === 'CRITICAL' ? 'danger' : diagnosisReport.risk_level === 'HIGH' ? 'warning' : 'info'">{{ diagnosisReport.risk_level }}</el-tag>
        </div>
        <div v-if="!feedbackGiven" class="section feedback">
          <div class="section-title">评价诊断结果</div>
          <div class="fb-btns">
            <el-button size="small" type="success" @click="submitFeedback('accurate')" :icon="'Check'">准确</el-button>
            <el-button size="small" type="warning" @click="submitFeedback('partially_accurate')">部分准确</el-button>
            <el-button size="small" type="danger" @click="submitFeedback('inaccurate')">不准确</el-button>
          </div>
        </div>
        <div v-else class="feedback-result">{{ feedbackResult }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.diagnostic-page { display: flex; gap: 16px; height: calc(100vh - 100px); }
.chat-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.msg { max-width: 80%; padding: 10px 16px; border-radius: 10px; font-size: 14px; line-height: 1.6;
  &.user { align-self: flex-end; background: rgba(0, 102, 255, 0.3); }
  &.assistant { align-self: flex-start; background: rgba(10, 22, 40, 0.8); border: 1px solid rgba(0, 240, 255, 0.1); }
  .msg-time { font-size: 10px; opacity: 0.4; margin-top: 4px; }
}
.streaming { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.typing-dots span { display: inline-block; width: 6px; height: 6px; background: var(--color-accent); border-radius: 50%; margin: 0 2px; animation: bounce 1.4s infinite both;
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}
@keyframes bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }
.step-text { font-size: 12px; color: var(--color-accent); }
.stream-preview { font-size: 13px; color: var(--color-text-secondary); white-space: pre-wrap; }
.quick-actions { padding: 8px 16px; display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid rgba(0, 240, 255, 0.05); }
.input-row { padding: 12px 16px; border-top: 1px solid rgba(0, 240, 255, 0.08); }
.report-sidebar { width: 340px; flex-shrink: 0; overflow-y: auto; }
.report-card { h4 { color: var(--color-accent); margin-bottom: 14px; } }
.section { margin-bottom: 16px; }
.section-title { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 8px; font-weight: 600; }
.cause-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(0, 240, 255, 0.05); font-size: 13px; }
.cause-rank { font-weight: 700; color: var(--color-accent); }
.cause-text { flex: 1; }
.cause-prob { font-weight: 700; white-space: nowrap; }
.feedback { .fb-btns { display: flex; gap: 6px; } }
.feedback-result { font-size: 13px; color: #52c41a; }
</style>
