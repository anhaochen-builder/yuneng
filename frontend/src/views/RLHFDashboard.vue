<template>
  <div class="rlhf-page">
    <div class="page-header">
      <h2>RLHF 反馈驱动优化</h2>
      <div class="actions">
        <button class="btn-primary" @click="prepareDataset" :disabled="!readyForTraining">
          {{ readyForTraining ? '准备微调数据集' : `还需${status.feedback?.remaining || 0}条准确反馈` }}
        </button>
        <button class="btn-secondary" @click="trainModel" :disabled="datasets.length === 0">触发微调</button>
      </div>
    </div>

    <div class="status-grid">
      <div class="status-card">
        <span class="s-value">{{ status.feedback?.total || 0 }}</span>
        <span class="s-label">总反馈</span>
      </div>
      <div class="status-card accurate">
        <span class="s-value">{{ status.feedback?.accurate || 0 }}</span>
        <span class="s-label">准确 (正样本)</span>
      </div>
      <div class="status-card">
        <span class="s-value">{{ status.feedback?.partially_accurate || 0 }}</span>
        <span class="s-label">部分准确</span>
      </div>
      <div class="status-card inaccurate">
        <span class="s-value">{{ status.feedback?.inaccurate || 0 }}</span>
        <span class="s-label">不准确 (负样本)</span>
      </div>
      <div class="status-card" :class="{ ready: readyForTraining }">
        <span class="s-value">{{ readyForTraining ? '✅ 达标' : '❌ 未达标' }}</span>
        <span class="s-label">阈值: 50条准确</span>
      </div>
    </div>

    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
      <span class="progress-text">{{ status.feedback?.accurate || 0 }} / 50</span>
    </div>

    <div class="section" v-if="datasets.length">
      <h3>微调数据集</h3>
      <div v-for="d in datasets" :key="d.name" class="dataset-card">
        <span class="ds-name">{{ d.name }}</span>
        <span class="ds-tag pos">+{{ d.positive }} 正样本</span>
        <span class="ds-tag neg">-{{ d.negative }} 负样本</span>
        <span class="ds-total">{{ d.total }} 条</span>
      </div>
    </div>

    <div class="section" v-if="versions.length">
      <h3>模型版本</h3>
      <div v-for="v in versions" :key="v.id" class="version-card" :class="{ active: v.id === activeVersion }">
        <span class="v-id">v{{ v.id }}</span>
        <span class="v-samples">{{ v.samples }} 样本</span>
        <span class="v-date">{{ v.created_at?.slice(0, 10) }}</span>
        <span v-if="v.id === activeVersion" class="v-active">当前</span>
        <button v-else class="btn-small" @click="deployVersion(v.id)">部署</button>
      </div>
    </div>

    <div class="section">
      <h3>手动录入反馈</h3>
      <div class="form-row">
        <input v-model="form.task_id" placeholder="任务ID" class="input" />
        <select v-model="form.rating" class="input">
          <option value="accurate">准确</option>
          <option value="partially_accurate">部分准确</option>
          <option value="inaccurate">不准确</option>
        </select>
        <input v-model="form.comment" placeholder="评价备注" class="input" />
        <button class="btn-primary" @click="submitFeedback">提交</button>
      </div>
    </div>

    <div class="section" v-if="recent.length">
      <h3>最近反馈</h3>
      <div v-for="r in recent" :key="r.feedback_id" class="fb-card">
        <span class="fb-id">{{ r.task_id }}</span>
        <span class="fb-rating" :class="r.rating">{{ ratingLabel(r.rating) }}</span>
        <span class="fb-comment">{{ r.comment || r.corrected_root_cause || '-' }}</span>
        <span class="fb-time">{{ r.created_at?.slice(0, 16) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

interface RlhfStatus { feedback: { total: number; accurate: number; partially_accurate: number; inaccurate: number; threshold: number; remaining: number; ready: boolean }; datasets: { name: string; total: number; positive: number; negative: number }[]; model_versions: { versions: { id: string; samples: number; created_at: string }[]; active: string | null }; recent_feedback: { feedback_id: string; task_id: string; rating: string; comment: string; corrected_root_cause: string; created_at: string }[] }

const status = ref<RlhfStatus>({ feedback: { total: 0, accurate: 0, partially_accurate: 0, inaccurate: 0, threshold: 50, remaining: 50, ready: false }, datasets: [], model_versions: { versions: [], active: null }, recent_feedback: [] })
const form = ref({ task_id: '', rating: 'accurate', comment: '' })

const readyForTraining = computed(() => status.value.feedback?.ready || false)
const progressPct = computed(() => Math.min(100, ((status.value.feedback?.accurate || 0) / 50) * 100))
const datasets = computed(() => status.value.datasets || [])
const versions = computed(() => status.value.model_versions?.versions || [])
const activeVersion = computed(() => status.value.model_versions?.active)
const recent = computed(() => (status.value.recent_feedback || []).slice(0, 10))

function ratingLabel(r: string) { return { accurate: '准确', partially_accurate: '部分准确', inaccurate: '不准确' }[r] || r }

async function loadStatus() { const { data } = await api.get('/api/rlhf/status'); status.value = (data as { data: RlhfStatus }).data }
async function submitFeedback() { await api.post('/api/rlhf/feedback', form.value); form.value.task_id = ''; form.value.comment = ''; loadStatus() }
async function prepareDataset() { await api.post('/api/rlhf/prepare'); loadStatus() }
async function trainModel() { await api.post('/api/rlhf/train'); loadStatus() }
async function deployVersion(v: string) { await api.post('/api/rlhf/deploy', { version: v }); loadStatus() }

onMounted(loadStatus)
</script>

<style scoped>
.rlhf-page { max-width: 1200px; margin: 0 auto; padding: 24px; color: #e0e0e0; overflow-y: auto; max-height: calc(100vh - 140px); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { color: #2FA7D1; margin: 0; font-size: 1.3em; }
.actions { display: flex; gap: 10px; }
.btn-primary { padding: 8px 18px; background: #2FA7D1; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 8px 18px; background: #1E3A5F; color: #2FA7D1; border: 1px solid #2FA7D1; border-radius: 4px; cursor: pointer; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.status-grid { display: flex; gap: 12px; margin-bottom: 16px; }
.status-card { flex: 1; background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 14px; text-align: center; }
.status-card.accurate { border-color: rgba(64,201,160,0.3); }
.status-card.inaccurate { border-color: rgba(232,85,85,0.3); }
.status-card.ready { border-color: #40C9A0; box-shadow: 0 0 12px rgba(64,201,160,0.2); }
.s-value { display: block; font-size: 1.6em; font-weight: 700; color: #2FA7D1; font-family: monospace; }
.s-label { display: block; font-size: 0.75em; color: #5A7A9A; margin-top: 4px; }

.progress-bar { position: relative; height: 28px; background: #0A1628; border-radius: 4px; margin-bottom: 20px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #2FA7D1, #40C9A0); border-radius: 4px; transition: width 0.5s; }
.progress-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #fff; font-size: 0.8em; font-weight: 600; }

.section { background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
.section h3 { color: #2FA7D1; font-size: 0.95em; margin-bottom: 12px; }

.dataset-card, .version-card, .fb-card { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(30,58,95,0.5); font-size: 0.85em; }
.ds-name { color: #2FA7D1; font-family: monospace; flex: 1; }
.ds-tag { padding: 2px 8px; border-radius: 3px; font-size: 0.75em; }
.ds-tag.pos { background: rgba(64,201,160,0.2); color: #40C9A0; }
.ds-tag.neg { background: rgba(232,85,85,0.2); color: #E85555; }
.ds-total { color: #8EA8C8; }
.v-id { color: #2FA7D1; font-family: monospace; }
.v-active { color: #40C9A0; font-weight: 600; }
.v-date, .v-samples { color: #5A7A9A; }
.version-card.active { border-color: rgba(64,201,160,0.3); background: rgba(64,201,160,0.05); }
.btn-small { padding: 4px 12px; background: #1E3A5F; border: 1px solid #2FA7D1; color: #2FA7D1; border-radius: 3px; cursor: pointer; font-size: 0.75em; }

.form-row { display: flex; gap: 10px; }
.input { padding: 8px 12px; background: #0A1628; border: 1px solid #1E3A5F; color: #e0e0e0; border-radius: 4px; }
.input:first-child { flex: 1; }

.fb-rating { padding: 2px 8px; border-radius: 3px; font-size: 0.75em; }
.fb-rating.accurate { background: rgba(64,201,160,0.2); color: #40C9A0; }
.fb-rating.partially_accurate { background: rgba(240,160,64,0.2); color: #F0A040; }
.fb-rating.inaccurate { background: rgba(232,85,85,0.2); color: #E85555; }
.fb-comment { flex: 1; color: #A0B8D0; font-size: 0.82em; }
.fb-time { color: #5A7A9A; font-size: 0.75em; }
</style>
