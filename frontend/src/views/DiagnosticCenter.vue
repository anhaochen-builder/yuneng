<script setup lang="ts">
import { ref, nextTick, watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSSE } from '@/hooks/useSSE'
import { feedbackApi } from '@/api'
import http from '@/api'

interface ChatMsg {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  taskId?: string
  report?: any
  streaming?: boolean
}

const route = useRoute()
const { isStreaming, currentStep, streamedContent, diagnosisReport, error, sendMessage } = useSSE()
const inputText = ref('')
const chatMessages = ref<ChatMsg[]>([])
const messagesEnd = ref<HTMLElement | null>(null)
const chatContainer = ref<HTMLElement | null>(null)
const feedbackGiven = ref(false)
const feedbackResult = ref('')
const showHistory = ref(false)
const historyLoaded = ref(false)
const loadingHistory = ref(false)
const historySessions = ref<any[]>([])

// 诊断历史
async function loadHistory() {
  if (historyLoaded.value) return
  loadingHistory.value = true
  try {
    const res = await http.get('/api/diagnose/history')
    historySessions.value = res.data?.history || []
    historyLoaded.value = true
  } catch (e) {
    historySessions.value = []
  } finally {
    loadingHistory.value = false
  }
}

function restoreHistory(session: any) {
  chatMessages.value = [
    { role: 'user', content: session.user, timestamp: '' },
    { role: 'assistant', content: session.assistant, timestamp: '' },
  ]
  showHistory.value = false
}

// 多模态
const uploadedImages = ref<Array<{ file: File; preview: string; type: string }>>([])
const uploadedAudio = ref<Array<{ file: File; name: string }>>([])
const showUploadPanel = ref(false)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const audioInput = ref<HTMLInputElement | null>(null)

const quickActions = [
  '3号逆变器通讯中断，后台报ALM-001',
  '1号风机齿轮箱油温超过80°C，振动值升高',
  '变压器油温异常，当前85°C，DGA氢气超标',
  '光伏逆变器直流侧绝缘阻抗降低至300kΩ',
]

function scrollBottom() { nextTick(() => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
})}

// 保留最近 N 轮诊断上下文
watch(chatMessages, () => {
  if (chatMessages.value.length > 20) {
    chatMessages.value = chatMessages.value.slice(-20)
  }
}, { deep: true })

async function send() {
  const text = inputText.value.trim()
  const hasMulti = hasFiles()
  if ((!text && !hasMulti) || isStreaming.value) return

  let displayText = text || '多模态故障诊断'
  if (hasMulti) {
    const parts: string[] = [text || '请根据以下多模态数据诊断故障']
    if (uploadedImages.value.length) parts.push(`📷 已上传${uploadedImages.value.length}张图片(${uploadedImages.value.map(i=>i.type).join('/')})`)
    if (uploadedAudio.value.length) parts.push(`🎵 已上传${uploadedAudio.value.length}个音频文件`)
    displayText = parts.join('\n')
  }

  chatMessages.value.push({ role: 'user', content: displayText, timestamp: new Date().toLocaleTimeString() })
  inputText.value = ''
  feedbackGiven.value = false
  await scrollBottom()

  // 插入占位消息，实时更新
  const assistantMsg: ChatMsg = { role: 'assistant', content: '', timestamp: new Date().toLocaleTimeString(), streaming: true }
  chatMessages.value.push(assistantMsg)

  const apiBase = import.meta.env.VITE_API_BASE_URL || ''
  const streamUrl = hasMulti
    ? `${apiBase}/api/diagnose/multimodal/stream`
    : `${apiBase}/api/diagnose/stream`

  await sendMessage(streamUrl, { symptoms: text || '多模态故障诊断' })

  // 流式完成后更新消息
  assistantMsg.streaming = false
  assistantMsg.content = streamedContent.value || '诊断完成'
  assistantMsg.report = diagnosisReport.value || undefined
  if (diagnosisReport.value?.task_id) {
    assistantMsg.taskId = diagnosisReport.value.task_id
  }

  // 清理上传文件
  uploadedImages.value.forEach(i => URL.revokeObjectURL(i.preview))
  uploadedImages.value = []
  uploadedAudio.value = []
  showUploadPanel.value = false

  if (error.value) {
    assistantMsg.content = `❌ 诊断失败: ${error.value}`
  }

  scrollBottom()
}

function useQuick(text: string) { inputText.value = text; send() }

// 实时同步流式内容到最新 assistant 消息
watch([streamedContent, currentStep, diagnosisReport], () => {
  const last = chatMessages.value[chatMessages.value.length - 1]
  if (last && last.role === 'assistant' && last.streaming) {
    last.content = streamedContent.value || currentStep.value || ''
    last.report = diagnosisReport.value || undefined
    scrollBottom()
  }
})

// 多模态文件处理
function handleImageDrop(e: DragEvent) {
  isDragging.value = false
  addImageFiles(e.dataTransfer?.files)
}
function handleImageSelect() { addImageFiles(fileInput.value?.files) }

function addImageFiles(fileList: FileList | null | undefined) {
  if (!fileList) return
  for (let i = 0; i < fileList.length; i++) {
    const f = fileList[i]
    if (!f || !f.type.startsWith('image/')) continue
    const preview = URL.createObjectURL(f)
    const imgType = f.name.toLowerCase().includes('红外') || f.name.toLowerCase().includes('thermal') ? '红外热像' : '可见光'
    uploadedImages.value.push({ file: f, preview, type: imgType })
  }
}

function removeImage(idx: number) {
  const img = uploadedImages.value[idx]
  if (img) URL.revokeObjectURL(img.preview)
  uploadedImages.value.splice(idx, 1)
}

function handleAudioSelect() {
  const files = audioInput.value?.files
  if (!files) return
  for (let i = 0; i < files.length; i++) {
    const f = files[i]
    if (!f || (!f.type.startsWith('audio/') && !f.name.endsWith('.wav') && !f.name.endsWith('.mp3') && !f.name.endsWith('.flac'))) continue
    uploadedAudio.value.push({ file: f, name: f.name })
  }
}
function removeAudio(idx: number) { uploadedAudio.value.splice(idx, 1) }
function hasFiles() { return uploadedImages.value.length > 0 || uploadedAudio.value.length > 0 }

async function submitFeedback(rating: string) {
  const last = [...chatMessages.value].reverse().find(m => m.role === 'assistant' && m.taskId)
  if (!last?.taskId) return
  try {
    await feedbackApi.submit(last.taskId, rating)
    feedbackGiven.value = true
    feedbackResult.value = rating === 'accurate' ? '✅ 感谢反馈！案例已入库' : '📝 感谢反馈，已记录'
  } catch { feedbackResult.value = '反馈提交失败' }
}

function clearChat() {
  chatMessages.value = []
  feedbackGiven.value = false
  feedbackResult.value = ''
}

function retry() {
  const lastUser = [...chatMessages.value].reverse().find(m => m.role === 'user')
  if (lastUser) {
    chatMessages.value = chatMessages.value.filter(m => m.role !== 'assistant')
    inputText.value = lastUser.content
    send()
  }
}

function getLastTaskId() {
  const last = [...chatMessages.value].reverse().find(m => m.role === 'assistant' && m.taskId)
  return last?.taskId
}

const q = route.query.q as string
if (q) { inputText.value = q; setTimeout(send, 500) }

onMounted(() => { loadHistory() })
</script>

<template>
  <div class="diagnostic-page animate-fade-in">
    <!-- 全宽对话框 -->
    <div class="chat-panel tech-card">
      <div class="chat-header">
        <h4>🔧 智能诊断对话</h4>
        <div class="chat-header-actions">
          <el-button size="small" text @click="showHistory = !showHistory" :type="showHistory ? 'primary' : 'default'">
            <el-icon><component is="Clock" /></el-icon> 历史
          </el-button>
          <el-button size="small" text @click="showUploadPanel = !showUploadPanel" :type="showUploadPanel ? 'primary' : 'default'">
            <el-icon><component is="Upload" /></el-icon> 多模态
          </el-button>
          <el-button size="small" text @click="clearChat" :disabled="!chatMessages.length">
            <el-icon><component is="Delete" /></el-icon> 清空
          </el-button>
        </div>
      </div>

      <!-- 历史面板 -->
      <div v-if="showHistory" class="history-panel animate-slide-up">
        <div class="history-header">
          <span>诊断历史 ({{ historySessions.length }}条)</span>
          <el-button size="small" text @click="loadHistory" :loading="loadingHistory">刷新</el-button>
        </div>
        <div class="history-list" v-if="historySessions.length">
          <div v-for="(h, i) in historySessions" :key="i" class="history-item" @click="restoreHistory(h)">
            <div class="hi-user">{{ h.user?.slice(0, 80) }}{{ (h.user?.length || 0) > 80 ? '...' : '' }}</div>
            <div class="hi-assistant">{{ h.assistant?.slice(0, 120) }}{{ (h.assistant?.length || 0) > 120 ? '...' : '' }}</div>
          </div>
        </div>
        <div v-else class="history-empty">暂无诊断历史</div>
      </div>

      <!-- 多模态导入面板 -->
      <div v-if="showUploadPanel" class="upload-panel animate-slide-up">
        <div class="upload-section">
          <div class="upload-label">📷 设备图像</div>
          <div
            class="upload-zone" :class="{ dragging: isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="handleImageDrop"
            @click="fileInput?.click()"
          >
            <input type="file" accept="image/*" multiple ref="fileInput" @change="handleImageSelect" style="display:none" />
            <el-icon :size="24" color="rgba(0,240,255,0.3)"><component is="PictureFilled" /></el-icon>
            <span>红外热像 / 设备照片</span>
          </div>
          <div v-if="uploadedImages.length" class="preview-row">
            <div v-for="(img, i) in uploadedImages" :key="i" class="preview-item">
              <img :src="img.preview" />
              <span class="preview-tag">{{ img.type }}</span>
              <el-button size="small" circle text type="danger" @click.stop="removeImage(i)">✕</el-button>
            </div>
          </div>
        </div>
        <div class="upload-section">
          <div class="upload-label">🎵 设备声音</div>
          <div class="upload-zone" @click="audioInput?.click()">
            <input type="file" accept="audio/*,.wav,.mp3,.flac" ref="audioInput" @change="handleAudioSelect" style="display:none" />
            <el-icon :size="24" color="rgba(0,240,255,0.3)"><component is="Headset" /></el-icon>
            <span>异常声音 / 振动录音</span>
          </div>
          <div v-if="uploadedAudio.length" class="audio-list">
            <div v-for="(a, i) in uploadedAudio" :key="i" class="audio-item">
              <el-icon color="var(--color-accent)"><component is="VideoPlay" /></el-icon>
              <span>{{ a.name }}</span>
              <el-button size="small" circle text type="danger" @click.stop="removeAudio(i)">✕</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 聊天消息区 -->
      <div class="chat-messages" ref="chatContainer" @scroll.passive>
        <div v-if="!chatMessages.length && !isStreaming" class="welcome-state">
          <div class="welcome-icon">🩺</div>
          <p class="welcome-title">新能源场站智能诊断</p>
          <p class="welcome-desc">输入故障现象，AI 多智能体协同诊断</p>
          <div class="welcome-features">
            <span>🔍 根因分析</span>
            <span>📋 处置方案</span>
            <span>🛡 安规审查</span>
            <span>📊 数据支撑</span>
          </div>
        </div>

        <div v-for="(msg, i) in chatMessages" :key="i" :class="['msg', msg.role]">
          <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : msg.role === 'system' ? '📢' : '🤖' }}</div>
          <div class="msg-body">
            <!-- 系统消息 -->
            <template v-if="msg.role === 'system'">
              <div class="msg-content">{{ msg.content }}</div>
            </template>

            <!-- 用户消息 -->
            <template v-else-if="msg.role === 'user'">
              <div class="msg-content">{{ msg.content }}</div>
              <div class="msg-time">{{ msg.timestamp }}</div>
            </template>

            <!-- 助手消息 — 包含实时流 + 结构化报告 -->
            <template v-else>
              <!-- 流式进行中 -->
              <div v-if="msg.streaming" class="msg-content">
                <div class="streaming-header">
                  <span class="typing-dots"><span></span><span></span><span></span></span>
                  <span class="step-text">{{ currentStep || '诊断中...' }}</span>
                </div>
                <div class="stream-preview" v-if="streamedContent || msg.content">{{ msg.content }}</div>
                <div v-else class="stream-placeholder">
                  <span class="sp-item">🔍 正在检索历史案例...</span>
                  <span class="sp-item">📊 正在分析设备数据...</span>
                  <span class="sp-item">🧠 正在推理根因...</span>
                </div>
              </div>

              <!-- 流式完成 — 显示完整报告 -->
              <div v-else class="msg-content report-content">
                <!-- 报告头部: 置信度 + 风险等级 -->
                <div class="report-card-wrap">
                  <div class="rc-header">
                    <span class="rc-title">📋 诊断报告</span>
                    <div class="rc-badges">
                      <el-tag v-if="msg.report?.risk_level"
                        :type="msg.report.risk_level === 'CRITICAL' ? 'danger' : msg.report.risk_level === 'HIGH' ? 'warning' : 'info'"
                        effect="dark" size="small">
                        {{ msg.report.risk_level }}
                      </el-tag>
                      <span v-if="msg.report?.confidence" class="rc-confidence font-digital"
                        :style="{ color: (msg.report.confidence || 0) > 0.85 ? '#52c41a' : (msg.report.confidence || 0) > 0.7 ? '#ff9c40' : '#ff4d4f' }">
                        {{ ((msg.report.confidence || 0) * 100).toFixed(0) }}%
                      </span>
                    </div>
                  </div>

                  <!-- 根因列表 -->
                  <div v-if="msg.report?.root_causes?.length" class="rc-section">
                    <div class="rc-section-title">🔍 可能原因</div>
                    <div v-for="(c, j) in msg.report.root_causes" :key="j" class="rc-cause">
                      <span class="rc-cause-rank">#{{ Number(j) + 1 }}</span>
                      <span class="rc-cause-text">{{ c.cause }}</span>
                      <el-progress
                        :percentage="Math.round((c.probability || 0) * 100)"
                        :color="(c.probability || 0) > 0.7 ? '#ff4d4f' : (c.probability || 0) > 0.4 ? '#ff9c40' : '#52c41a'"
                        :stroke-width="6"
                        style="flex-shrink:0;width:100px"
                      />
                    </div>
                  </div>

                  <!-- 文本内容 -->
                  <div v-if="msg.content" class="rc-section">
                    <div class="rc-section-title">📝 分析详情</div>
                    <div class="rc-text" v-html="msg.content.replace(/\n/g, '<br>')"></div>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="rc-actions">
                    <span class="msg-time">{{ msg.timestamp }}</span>
                    <div class="rc-action-btns">
                      <el-button size="small" text @click="retry" :disabled="isStreaming">🔄 重试</el-button>
                      <el-button size="small" text @click="copyReport(msg)">📋 复制</el-button>
                    </div>
                  </div>

                  <!-- 反馈 -->
                  <div class="rc-feedback" v-if="!feedbackGiven">
                    <span class="fb-label">这个诊断有帮助吗？</span>
                    <el-button size="small" type="success" @click="submitFeedback('accurate')" plain>👍 准确</el-button>
                    <el-button size="small" type="warning" @click="submitFeedback('partially_accurate')" plain>🤔 部分准确</el-button>
                    <el-button size="small" type="danger" @click="submitFeedback('inaccurate')" plain>👎 不准确</el-button>
                  </div>
                  <div v-else class="rc-feedback-result">{{ feedbackResult }}</div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <div ref="messagesEnd"></div>
      </div>

      <!-- 错误提示 -->
      <div v-if="error && !isStreaming" class="error-bar">
        <span>❌ {{ error }}</span>
        <el-button size="small" text type="danger" @click="retry">重试</el-button>
        <el-button size="small" text @click="error = ''">关闭</el-button>
      </div>

      <!-- 快捷操作 -->
      <div class="quick-actions">
        <el-button v-for="act in quickActions" :key="act" size="small" text @click="useQuick(act)" :disabled="isStreaming">
          {{ act.slice(0, 35) }}...
        </el-button>
      </div>

      <!-- 输入区 -->
      <div class="input-row">
        <el-input
          v-model="inputText"
          placeholder="描述故障现象，如：3号逆变器通讯中断，后台报ALM-001..."
          @keyup.enter="send"
          :disabled="isStreaming"
          size="large"
          clearable
        >
          <template #prefix>
            <el-icon><component is="ChatDotRound" /></el-icon>
          </template>
          <template #append>
            <el-button @click="send" :disabled="isStreaming || (!inputText.trim() && !hasFiles())" type="primary" style="min-width:100px">
              <el-icon v-if="isStreaming" class="is-loading"><component is="Loading" /></el-icon>
              {{ isStreaming ? '诊断中' : '发送诊断' }}
            </el-button>
          </template>
        </el-input>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
function copyReport(msg: any) {
  let text = '诊断报告\n'
  if (msg.report?.root_causes?.length) {
    text += '\n可能原因:\n'
    msg.report.root_causes.forEach((c: any, j: number) => {
      text += `  #${j+1} ${c.cause} (${Math.round((c.probability||0)*100)}%)\n`
    })
  }
  if (msg.content) text += `\n分析详情:\n${msg.content}\n`
  navigator.clipboard.writeText(text).catch(() => {})
}
</script>

<style scoped lang="scss">
.diagnostic-page {
  display: flex; gap: 14px; height: calc(100vh - 130px); padding: 8px 16px;
}

.chat-panel {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;

  .chat-header {
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 10px; border-bottom: 1px solid rgba(0,240,255,0.08); margin-bottom: 8px;
    h4 { color: var(--color-accent); font-size: 14px; margin: 0; }
    .chat-header-actions { display: flex; gap: 4px; }
  }
}

// ── 历史面板 ──
.history-panel {
  padding: 8px 12px 12px; border-bottom: 1px solid rgba(0,240,255,0.06);
  background: rgba(0,240,255,0.02); max-height: 220px; overflow-y: auto;
}
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px; color: var(--color-text-secondary); }
.history-list { display: flex; flex-direction: column; gap: 6px; }
.history-item {
  padding: 8px 10px; background: rgba(0,240,255,0.03); border-radius: 6px;
  border: 1px solid rgba(0,240,255,0.06); cursor: pointer; transition: border-color 0.2s;
  &:hover { border-color: var(--color-accent); }
}
.hi-user { font-size: 12px; color: var(--color-text-primary); margin-bottom: 3px; }
.hi-assistant { font-size: 11px; color: var(--color-text-secondary); opacity: 0.75; }
.history-empty { text-align: center; font-size: 12px; color: var(--color-text-secondary); padding: 16px; }

// ── 聊天消息区 ──
.chat-messages {
  flex: 1; overflow-y: auto; padding: 12px 4px;
  display: flex; flex-direction: column; gap: 12px;
}

.welcome-state {
  text-align: center; padding: 40px 20px;
  .welcome-icon { font-size: 48px; margin-bottom: 12px; }
  .welcome-title { font-size: 18px; color: var(--color-accent); font-weight: 700; margin-bottom: 8px; }
  .welcome-desc { font-size: 13px; color: var(--color-text-secondary); }
  .welcome-features { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; }
  .welcome-features span { padding: 4px 12px; background: rgba(0,240,255,0.06); border-radius: 12px; font-size: 12px; color: var(--color-text-secondary); border: 1px solid rgba(0,240,255,0.1); }
}

.msg {
  display: flex; gap: 10px;
  &.user { align-self: flex-end; flex-direction: row-reverse; }
  &.assistant, &.system { align-self: flex-start; }

  .msg-avatar { font-size: 22px; flex-shrink: 0; width: 32px; text-align: center; }
  .msg-body { flex: 1; min-width: 0; }
  .msg-content {
    padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.7;
    color: var(--color-text-primary);
  }
  &.user .msg-content { background: rgba(0,102,255,0.25); border: 1px solid rgba(0,102,255,0.2); max-width: 85%; margin-left: auto; }
  &.assistant .msg-content { background: rgba(10,22,40,0.85); border: 1px solid rgba(0,240,255,0.1); }
  &.system .msg-content { background: rgba(255,156,64,0.1); border: 1px solid rgba(255,156,64,0.15); font-size: 12px; text-align: center; }
  .msg-time { font-size: 10px; color: var(--color-text-secondary); margin-top: 4px; padding: 0 4px; }
}

// 流式动画
.streaming-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.typing-dots span {
  display: inline-block; width: 6px; height: 6px; background: var(--color-accent);
  border-radius: 50%; margin: 0 2px; animation: bounce 1.4s infinite both;
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}
@keyframes bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }
.step-text { font-size: 12px; color: var(--color-accent); }
.stream-preview { font-size: 13px; color: var(--color-text-secondary); white-space: pre-wrap; padding: 6px 0;  }
.stream-placeholder { .sp-item { display: block; font-size: 12px; color: rgba(255,255,255,0.3); padding: 2px 0; animation: pulse-text 2s ease-in-out infinite; &:nth-child(2){animation-delay:0.4s;} &:nth-child(3){animation-delay:0.8s;} } }
@keyframes pulse-text { 0%,100%{opacity:0.3;} 50%{opacity:0.7;} }

// ── 报告卡片（嵌入聊天） ──
.report-content { padding: 0 !important; background: transparent !important; border: none !important; }
.report-card-wrap {
  background: rgba(10,22,40,0.9); border: 1px solid rgba(0,240,255,0.15); border-radius: 12px; padding: 16px 18px;
}
.rc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.rc-title { font-size: 16px; color: var(--color-accent); font-weight: 700; }
.rc-badges { display: flex; align-items: center; gap: 10px; }
.rc-confidence { font-size: 20px; font-weight: 700; }
.rc-section { margin-bottom: 14px; &:last-child { margin-bottom: 0; } }
.rc-section-title { font-size: 14px; color: var(--color-accent); margin-bottom: 8px; font-weight: 600; }
.rc-cause { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(0,240,255,0.04); border-radius: 6px; margin-bottom: 6px; border: 1px solid rgba(0,240,255,0.06); }
.rc-cause-rank { font-weight: 700; color: var(--color-accent); font-size: 14px; min-width: 24px; }
.rc-cause-text { flex: 1; font-size: 14px; }
.rc-text { font-size: 14px; color: var(--color-text-secondary); line-height: 1.85; }
.rc-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 10px; border-top: 1px solid rgba(0,240,255,0.06); }
.rc-action-btns { display: flex; gap: 4px; }
.rc-feedback { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(0,240,255,0.06); flex-wrap: wrap; }
.fb-label { font-size: 13px; color: var(--color-text-secondary); margin-right: 4px; }
.rc-feedback-result { font-size: 13px; color: #52c41a; padding: 8px 0; margin-top: 6px; }

// ── 错误栏 ──
.error-bar {
  display: flex; align-items: center; gap: 8px; padding: 8px 14px;
  background: rgba(255,77,79,0.08); border-top: 1px solid rgba(255,77,79,0.15);
  font-size: 13px; color: var(--color-critical);
}

// ── 快捷操作 + 输入 ──
.quick-actions {
  padding: 8px 12px; display: flex; flex-wrap: wrap; gap: 4px;
  border-top: 1px solid rgba(0,240,255,0.05);
}
.input-row { padding: 10px 12px; border-top: 1px solid rgba(0,240,255,0.08); }

// ── 多模态上传面板 ──
.upload-panel {
  display: flex; gap: 12px; padding: 10px 12px;
  border-bottom: 1px solid rgba(0,240,255,0.06);
  background: rgba(0,240,255,0.02);
}
.upload-section { flex: 1; }
.upload-label { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; font-weight: 600; }
.upload-zone {
  border: 1.5px dashed rgba(0,240,255,0.15); border-radius: 6px;
  padding: 14px; text-align: center; cursor: pointer; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  color: var(--color-text-secondary); font-size: 12px;
  &:hover, &.dragging { border-color: var(--color-accent); background: rgba(0,240,255,0.03); }
}
.preview-row { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.preview-item {
  position: relative; width: 56px; height: 56px; border-radius: 4px; overflow: hidden;
  border: 1px solid rgba(0,240,255,0.2);
  img { width: 100%; height: 100%; object-fit: cover; }
  .preview-tag { position: absolute; bottom: 0; left: 0; right: 0; font-size: 9px; text-align: center; background: rgba(0,0,0,0.6); color: #fff; padding: 1px; }
  .el-button { position: absolute; top: 0; right: 0; }
}
.audio-list { margin-top: 6px; }
.audio-item { display: flex; align-items: center; gap: 6px; padding: 6px 8px; background: rgba(0,240,255,0.03); border-radius: 4px; font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
</style>
