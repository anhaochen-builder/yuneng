<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSSE } from '@/hooks/useSSE'
import { feedbackApi } from '@/api'
import LangGraphTopology from '@/components/LangGraphTopology.vue'
import MemorySystemPanel from '@/components/MemorySystemPanel.vue'

const route = useRoute()
const { isStreaming, currentStep, streamedContent, diagnosisReport, error, sendMessage, abort } = useSSE()
const inputText = ref('')
const chatMessages = ref<Array<{ role: string; content: string; timestamp: string }>>([])
const messagesEnd = ref<HTMLElement | null>(null)
const feedbackGiven = ref(false)
const feedbackResult = ref('')
const showTopology = ref(false)
const showMemory = ref(false)

// 多模态文件
const uploadedImages = ref<Array<{ file: File; preview: string; type: string }>>([])
const uploadedAudio = ref<Array<{ file: File; name: string }>>([])
const showUploadPanel = ref(false)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const audioInput = ref<HTMLInputElement | null>(null)

// 模拟拓扑步骤
const topoSteps = ref<Array<{ node: string; status: 'done' | 'running' | 'pending' | 'error' | 'retry' }>>([
  { node: 'START', status: 'done' },
  { node: 'PreCheck', status: 'done' },
  { node: 'ContextLoad', status: 'done' },
  { node: 'IntentRouter', status: 'running' },
  { node: 'DiagAgent', status: 'pending' },
  { node: 'JudgeEval', status: 'pending' },
  { node: 'SafetyReview', status: 'pending' },
  { node: 'FinalResponse', status: 'pending' },
  { node: 'MemorySave', status: 'pending' },
  { node: 'END', status: 'pending' },
])

const quickActions = [
  '3号逆变器通讯中断，后台报ALM-001',
  '1号风机齿轮箱油温超过80°C，振动值升高',
  '变压器油温异常，当前85°C，DGA氢气超标',
  '光伏逆变器直流侧绝缘阻抗降低至300kΩ',
]

const recentHistory = [
  { id: 'DX-20260804-001', desc: '1号风机振动超标停机', time: '10:32', risk: 'HIGH' },
  { id: 'DX-20260804-002', desc: '3号逆变器通讯中断', time: '09:15', risk: 'CRITICAL' },
  { id: 'DX-20260803-008', desc: '变压器油温异常', time: '昨天 16:40', risk: 'MEDIUM' },
]

function scrollBottom() { nextTick(() => messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })) }

async function send() {
  const text = inputText.value.trim()
  const hasMultimodal = hasFiles()
  if ((!text && !hasMultimodal) || isStreaming.value) return

  let displayText = text || '多模态故障诊断'
  if (hasMultimodal) {
    const parts: string[] = [text || '请根据以下多模态数据诊断故障']
    if (uploadedImages.value.length) parts.push(`📷 已上传${uploadedImages.value.length}张图片(${uploadedImages.value.map(i=>i.type).join('/')})`)
    if (uploadedAudio.value.length) parts.push(`🎵 已上传${uploadedAudio.value.length}个音频文件`)
    displayText = parts.join('\n')
  }

  chatMessages.value.push({ role: 'user', content: displayText, timestamp: new Date().toLocaleTimeString() })
  inputText.value = ''
  feedbackGiven.value = false
  showTopology.value = true
  await scrollBottom()

  simulateTopoSteps()

  const apiBase = import.meta.env.VITE_API_BASE_URL || ''
  if (hasMultimodal) {
    await sendMessage(`${apiBase}/api/diagnose/multimodal/stream`, { symptoms: text || '多模态故障诊断' })
  } else {
    await sendMessage(`${apiBase}/api/diagnose/stream`, { symptoms: text })
  }
  const content = streamedContent.value || '诊断完成，报告已生成'
  chatMessages.value.push({ role: 'assistant', content, timestamp: new Date().toLocaleTimeString() })

  // 清理上传文件
  uploadedImages.value.forEach(i => URL.revokeObjectURL(i.preview))
  uploadedImages.value = []
  uploadedAudio.value = []
  showUploadPanel.value = false

  await scrollBottom()
}

function simulateTopoSteps() {
  const steps = ['DiagAgent', 'JudgeEval', 'SafetyReview', 'FinalResponse', 'MemorySave', 'END']
  let delay = 800
  steps.forEach((node, i) => {
    setTimeout(() => {
      // 标记之前的为 done
      topoSteps.value.forEach(s => { if (s.status === 'running') s.status = 'done' })
      // 当前为 running
      const target = topoSteps.value.find(s => s.node === node)
      if (target) target.status = 'running'
    }, delay * (i + 1))
  })
  // 全部完成
  setTimeout(() => {
    topoSteps.value.forEach(s => { if (s.status === 'running') s.status = 'done' })
  }, delay * (steps.length + 1))
}

function useQuick(text: string) { inputText.value = text; send() }

// ── 多模态文件处理 ──
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
  if (!diagnosisReport.value) return
  try {
    await feedbackApi.submit(diagnosisReport.value.task_id || 'unknown', rating)
    feedbackGiven.value = true
    feedbackResult.value = rating === 'accurate' ? '✅ 感谢反馈！案例已入库' : '📝 感谢反馈，已记录'
  } catch { feedbackResult.value = '反馈提交失败' }
}

function clearChat() {
  chatMessages.value = []
  showTopology.value = false
  showMemory.value = false
}

const q = route.query.q as string
if (q) { inputText.value = q; setTimeout(send, 500) }
</script>

<template>
  <div class="diagnostic-page animate-fade-in">
    <!-- 左侧: 聊天面板 -->
    <div class="chat-panel tech-card">
      <div class="chat-header">
        <h4>🔧 智能诊断对话</h4>
        <div class="chat-header-actions">
          <el-button size="small" text @click="showUploadPanel = !showUploadPanel" :type="showUploadPanel ? 'primary' : 'default'">
            <el-icon><component is="Upload" /></el-icon> 多模态
          </el-button>
          <el-button size="small" text @click="showTopology = !showTopology" :type="showTopology ? 'primary' : 'default'">
            <el-icon><component is="Share" /></el-icon> 拓扑
          </el-button>
          <el-button size="small" text @click="showMemory = !showMemory" :type="showMemory ? 'primary' : 'default'">
            <el-icon><component is="Collection" /></el-icon> 记忆
          </el-button>
          <el-button size="small" text @click="clearChat">
            <el-icon><component is="Delete" /></el-icon> 清空
          </el-button>
        </div>
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

      <div class="chat-messages" ref="messagesEnd">
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
          <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="msg-body">
            <div class="msg-content" v-html="msg.content.replace(/\n/g, '<br>')"></div>
            <div class="msg-time">{{ msg.timestamp }}</div>
          </div>
        </div>

        <div v-if="isStreaming" class="msg assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-body">
            <div class="streaming">
              <span class="typing-dots"><span></span><span></span><span></span></span>
              <span class="step-text">{{ currentStep || '诊断中...' }}</span>
            </div>
            <div class="stream-preview">{{ streamedContent }}</div>
          </div>
        </div>
      </div>

      <div class="quick-actions">
        <el-button v-for="act in quickActions" :key="act" size="small" text @click="useQuick(act)" :disabled="isStreaming">
          {{ act.slice(0, 35) }}...
        </el-button>
      </div>

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
            <el-button @click="send" :disabled="isStreaming || !inputText.trim()" type="primary" style="min-width:100px">
              <el-icon v-if="isStreaming" class="is-loading"><component is="Loading" /></el-icon>
              {{ isStreaming ? '诊断中' : '发送诊断' }}
            </el-button>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 中间: 拓扑 + 最近历史 -->
    <div class="middle-panels" v-if="showTopology || chatMessages.length">
      <div class="tech-card" v-if="showTopology">
        <h4>🔄 诊断流程编排</h4>
        <LangGraphTopology :steps="topoSteps" />
      </div>

      <div class="tech-card" v-if="!showTopology && recentHistory.length">
        <h4>📋 最近诊断</h4>
        <div class="history-list">
          <div v-for="h in recentHistory" :key="h.id" class="history-item">
            <div class="hi-header">
              <span class="hi-id font-digital">{{ h.id }}</span>
              <el-tag size="small" :type="h.risk === 'CRITICAL' ? 'danger' : h.risk === 'HIGH' ? 'warning' : 'info'">{{ h.risk }}</el-tag>
            </div>
            <div class="hi-desc">{{ h.desc }}</div>
            <div class="hi-time">{{ h.time }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧: 报告 + 记忆面板 -->
    <div class="right-panels">
      <div class="tech-card report-card" v-if="diagnosisReport">
        <h4>🔧 诊断报告</h4>
        <div v-if="diagnosisReport.root_causes?.length" class="section">
          <div class="section-title">可能原因</div>
          <div v-for="(c, i) in diagnosisReport.root_causes" :key="i" class="cause-row">
            <span class="cause-rank">#{{ Number(i) + 1 }}</span>
            <span class="cause-text">{{ c.cause }}</span>
            <span class="cause-prob" :style="{ color: c.probability > 0.7 ? '#ff4d4f' : c.probability > 0.4 ? '#ff9c40' : '#52c41a' }">
              {{ ((Number(c.probability) || 0) * 100).toFixed(0) }}%
            </span>
          </div>
        </div>
        <div class="section">
          <div class="section-title">综合置信度</div>
          <el-progress :percentage="Math.round((Number(diagnosisReport.confidence) || 0) * 100)" :color="(p: number) => p > 70 ? '#52c41a' : p > 40 ? '#ff9c40' : '#ff4d4f'" :stroke-width="10" />
        </div>
        <div v-if="diagnosisReport.risk_level" class="section">
          <div class="section-title">风险等级</div>
          <el-tag :type="diagnosisReport.risk_level === 'CRITICAL' ? 'danger' : diagnosisReport.risk_level === 'HIGH' ? 'warning' : 'info'" size="large" effect="dark">
            {{ diagnosisReport.risk_level }}
          </el-tag>
        </div>
        <div v-if="diagnosisReport.suggestions?.length" class="section">
          <div class="section-title">处置建议</div>
          <div v-for="(s, i) in diagnosisReport.suggestions" :key="i" class="suggestion-item">
            <el-icon color="var(--color-accent)"><component is="Check" /></el-icon>
            <span>{{ s }}</span>
          </div>
        </div>
        <div v-if="!feedbackGiven" class="section feedback">
          <div class="section-title">评价诊断结果</div>
          <div class="fb-btns">
            <el-button size="small" type="success" @click="submitFeedback('accurate')" plain>👍 准确</el-button>
            <el-button size="small" type="warning" @click="submitFeedback('partially_accurate')" plain>🤔 部分准确</el-button>
            <el-button size="small" type="danger" @click="submitFeedback('inaccurate')" plain>👎 不准确</el-button>
          </div>
        </div>
        <div v-else class="feedback-result">{{ feedbackResult }}</div>
      </div>

      <MemorySystemPanel v-if="showMemory" 
        :short-term="[{ question: '逆变器通讯中断原因', answer: 'IGBT模块过热导致保护动作，通讯模块供电异常', time: '10:32' }]"
        :work-memory="{ intent: '故障诊断', confidence: 0.92, entities: { device: 'INV003', type: '通讯中断' }, judge_score: 85 }"
        :long-term="{ totalCases: 160, recentCases: [{ deviceType: '逆变器', faultType: '通讯中断', time: '2026-08-01', confidence: 0.88 }, { deviceType: '风机', faultType: '振动超标', time: '2026-07-30', confidence: 0.92 }] }"
      />

      <div v-if="error" class="tech-card error-card">
        <h4 style="color:var(--color-critical)">❌ 诊断出错</h4>
        <p>{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.diagnostic-page {
  display: flex; gap: 14px; height: calc(100vh - 130px); padding: 8px 16px;
}

// ── 聊天面板 ──
.chat-panel {
  flex: 1.4; display: flex; flex-direction: column; overflow: hidden;
  
  .chat-header {
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 10px; border-bottom: 1px solid rgba(0,240,255,0.08); margin-bottom: 8px;
    
    h4 { color: var(--color-accent); font-size: 14px; margin: 0; }
    .chat-header-actions { display: flex; gap: 4px; }
  }
}

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
  display: flex; gap: 10px; max-width: 92%;
  &.user { align-self: flex-end; flex-direction: row-reverse; }
  &.assistant { align-self: flex-start; }
  
  .msg-avatar { font-size: 22px; flex-shrink: 0; width: 32px; text-align: center; }
  .msg-body { flex: 1; }
  .msg-content {
    padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.7;
    color: var(--color-text-primary);
  }
  
  &.user .msg-content { background: rgba(0,102,255,0.25); border: 1px solid rgba(0,102,255,0.2); }
  &.assistant .msg-content { background: rgba(10,22,40,0.8); border: 1px solid rgba(0,240,255,0.1); }
  
  .msg-time { font-size: 10px; color: var(--color-text-secondary); margin-top: 4px; padding: 0 4px; }
}

.streaming { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; padding: 0 4px; }
.typing-dots span {
  display: inline-block; width: 6px; height: 6px; background: var(--color-accent);
  border-radius: 50%; margin: 0 2px; animation: bounce 1.4s infinite both;
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}
@keyframes bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }
.step-text { font-size: 12px; color: var(--color-accent); }
.stream-preview { font-size: 13px; color: var(--color-text-secondary); white-space: pre-wrap; padding: 8px 14px; }

.quick-actions {
  padding: 8px 12px; display: flex; flex-wrap: wrap; gap: 4px;
  border-top: 1px solid rgba(0,240,255,0.05);
}

.input-row {
  padding: 10px 12px; border-top: 1px solid rgba(0,240,255,0.08);
}

// ── 中间面板 ──
.middle-panels {
  width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px;
  overflow-y: auto;
  
  h4 { color: var(--color-accent); font-size: 13px; margin-bottom: 10px; }
}

.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-item {
  padding: 10px 12px; background: rgba(0,240,255,0.03); border-radius: 6px;
  border: 1px solid rgba(0,240,255,0.06); cursor: pointer; transition: border-color 0.2s;
  &:hover { border-color: var(--color-accent); }
}
.hi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.hi-id { font-size: 11px; color: var(--color-accent); }
.hi-desc { font-size: 13px; color: var(--color-text-primary); }
.hi-time { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }

// ── 右侧面板 ──
.right-panels {
  width: 300px; flex-shrink: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;
}

.report-card {
  h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }
}

.section { margin-bottom: 14px; }
.section-title { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; font-weight: 600; }
.cause-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.05); font-size: 13px; }
.cause-rank { font-weight: 700; color: var(--color-accent); min-width: 20px; }
.cause-text { flex: 1; }
.cause-prob { font-weight: 700; white-space: nowrap; }
.suggestion-item { display: flex; align-items: flex-start; gap: 6px; padding: 4px 0; font-size: 12px; color: var(--color-text-secondary); line-height: 1.5; }

.feedback { .fb-btns { display: flex; gap: 6px; flex-wrap: wrap; } }
.feedback-result { font-size: 13px; color: #52c41a; padding: 8px 0; }
.error-card { border-color: rgba(255,77,79,0.3); p { font-size: 13px; color: var(--color-text-secondary); } }

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
