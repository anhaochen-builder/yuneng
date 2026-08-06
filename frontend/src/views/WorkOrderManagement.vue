<template>
  <div class="workorder-page">
    <div class="page-header">
      <h2>智能工单</h2>
      <div class="header-stats">
        <span class="stat emergency">紧急: {{ stats.emergency_count }}</span>
        <span class="stat pending">待处理: {{ stats.pending }}</span>
        <span class="stat progress">处理中: {{ stats.in_progress }}</span>
        <span class="stat closed">已关闭: {{ stats.closed }}</span>
      </div>
    </div>

    <div class="filters">
      <select v-model="filterStatus" @change="loadOrders">
        <option value="">全部状态</option>
        <option value="pending">待派单</option>
        <option value="assigned">已派单</option>
        <option value="in_progress">维修中</option>
        <option value="pending_review">待验收</option>
        <option value="closed">已关闭</option>
      </select>
      <select v-model="filterLevel" @change="loadOrders">
        <option value="">全部级别</option>
        <option value="emergency">紧急</option>
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="order-list">
      <div v-for="order in orders" :key="order.order_id" class="order-card" :class="'level-' + order.level" @click="selectedOrder = order">
        <div class="order-header">
          <span class="order-id">{{ order.order_id }}</span>
          <span class="level-badge" :class="order.level">{{ levelLabel(order.level) }}</span>
          <span class="status-badge" :class="order.status">{{ statusLabel(order.status) }}</span>
        </div>
        <div class="order-title">{{ order.title }}</div>
        <div class="order-meta">
          <span>设备: {{ order.device_name || order.device_id }}</span>
          <span>创建: {{ formatTime(order.created_at) }}</span>
          <span v-if="order.assignee">责任人: {{ order.assignee }}</span>
        </div>
      </div>
      <div v-if="orders.length === 0" class="empty">暂无工单</div>
    </div>

    <div v-if="selectedOrder" class="modal-backdrop" @click.self="selectedOrder = null">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ selectedOrder.order_id }}</h3>
          <button class="close-btn" @click="selectedOrder = null">&times;</button>
        </div>
        <div class="modal-body">
          <div class="field">
            <label>标题</label>
            <p>{{ selectedOrder.title }}</p>
          </div>
          <div class="field">
            <label>设备</label>
            <p>{{ selectedOrder.device_name || selectedOrder.device_id }}</p>
          </div>
          <div class="field">
            <label>故障描述</label>
            <p class="desc">{{ selectedOrder.description }}</p>
          </div>
          <div class="field" v-if="selectedOrder.root_cause">
            <label>根因</label>
            <p>{{ selectedOrder.root_cause }}</p>
          </div>
          <div class="field" v-if="selectedOrder.investigation_steps.length">
            <label>排查步骤</label>
            <ol><li v-for="s in selectedOrder.investigation_steps" :key="s">{{ s }}</li></ol>
          </div>
          <div class="field" v-if="selectedOrder.recommendations.length">
            <label>处理建议</label>
            <ol><li v-for="r in selectedOrder.recommendations" :key="r">{{ r }}</li></ol>
          </div>
          <div class="field" v-if="selectedOrder.safety_notes.length">
            <label>安全提示</label>
            <div class="safety-notes">
              <div v-for="s in selectedOrder.safety_notes" :key="s" class="safety-item">{{ s }}</div>
            </div>
          </div>

          <div class="field">
            <label>状态变更</label>
            <div class="status-actions">
              <button v-for="s in nextStatuses" :key="s" class="status-btn" @click="updateStatus(s)">{{ statusLabel(s) }}</button>
            </div>
          </div>

          <div class="field">
            <label>责任人</label>
            <input v-model="assigneeInput" placeholder="输入责任人姓名" @keyup.enter="updateAssignee" />
            <button class="small-btn" @click="updateAssignee">确认</button>
          </div>

          <div class="field" v-if="selectedOrder.maintenance_notes">
            <label>维修备注</label>
            <p>{{ selectedOrder.maintenance_notes }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

interface Order {
  order_id: string; task_id: string; device_id: string; device_name: string
  title: string; description: string; root_cause: string
  investigation_steps: string[]; recommendations: string[]; safety_notes: string[]
  level: string; status: string; assignee: string
  created_at: string; updated_at: string; closed_at: string | null
  maintenance_notes: string; maintenance_images: string[]
}

const orders = ref<Order[]>([])
const stats = ref({ total: 0, pending: 0, in_progress: 0, closed: 0, emergency_count: 0, avg_resolution_hours: 0 })
const loading = ref(true)
const filterStatus = ref('')
const filterLevel = ref('')
const selectedOrder = ref<Order | null>(null)
const assigneeInput = ref('')

const TRANSITIONS: Record<string, string[]> = {
  pending: ['assigned', 'cancelled'],
  assigned: ['in_progress', 'cancelled'],
  in_progress: ['pending_review', 'assigned'],
  pending_review: ['closed', 'in_progress'],
  closed: [],
  cancelled: [],
}

const nextStatuses = computed(() => TRANSITIONS[selectedOrder.value?.status || ''] || [])

function statusLabel(s: string) {
  const m: Record<string, string> = { pending: '待派单', assigned: '已派单', in_progress: '维修中', pending_review: '待验收', closed: '已关闭', cancelled: '已取消' }
  return m[s] || s
}

function levelLabel(l: string) {
  const m: Record<string, string> = { emergency: '紧急', high: '高', medium: '中', low: '低' }
  return m[l] || l
}

function formatTime(t: string) {
  return t ? t.slice(0, 16).replace('T', ' ') : ''
}

async function loadOrders() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterLevel.value) params.set('level', filterLevel.value)
    const { data } = await api.get('/api/workorder?' + params.toString())
    orders.value = (data as { data: { orders: Order[] } }).data?.orders || []
  } catch { orders.value = [] }
  finally { loading.value = false }
}

async function loadStats() {
  const { data } = await api.get('/api/workorder/stats')
  stats.value = (data as { data: typeof stats.value }).data || stats.value
}

async function updateStatus(newStatus: string) {
  if (!selectedOrder.value) return
  await api.patch(`/api/workorder/${selectedOrder.value.order_id}`, { status: newStatus })
  selectedOrder.value.status = newStatus
  loadStats()
}

async function updateAssignee() {
  if (!selectedOrder.value || !assigneeInput.value) return
  await api.patch(`/api/workorder/${selectedOrder.value.order_id}`, { assignee: assigneeInput.value })
  selectedOrder.value.assignee = assigneeInput.value
  assigneeInput.value = ''
}

onMounted(() => { loadOrders(); loadStats() })
</script>

<style scoped>
.workorder-page { max-width: 1200px; margin: 0 auto; padding: 24px; color: #e0e0e0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { color: #2FA7D1; margin: 0; font-size: 1.4em; }
.header-stats { display: flex; gap: 16px; }
.stat { padding: 4px 12px; border-radius: 4px; font-size: 0.85em; }
.stat.emergency { background: rgba(232,85,85,0.15); color: #E85555; }
.stat.pending { background: rgba(240,160,64,0.15); color: #F0A040; }
.stat.progress { background: rgba(47,167,209,0.15); color: #2FA7D1; }
.stat.closed { background: rgba(64,201,160,0.15); color: #40C9A0; }

.filters { display: flex; gap: 12px; margin-bottom: 16px; }
.filters select { padding: 8px 12px; background: #0A1628; border: 1px solid #1E3A5F; color: #8EA8C8; border-radius: 4px; }

.order-list { display: flex; flex-direction: column; gap: 10px; }
.order-card { background: #0D1F35; border: 1px solid #1E3A5F; border-radius: 6px; padding: 14px 18px; cursor: pointer; transition: border-color 0.2s; }
.order-card:hover { border-color: #2FA7D1; }
.order-card.level-emergency { border-left: 3px solid #E85555; }
.order-card.level-high { border-left: 3px solid #F0A040; }

.order-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.order-id { font-family: monospace; color: #2FA7D1; font-size: 0.9em; }
.level-badge, .status-badge { padding: 2px 8px; border-radius: 3px; font-size: 0.75em; }
.level-badge.emergency { background: #E85555; color: #fff; }
.level-badge.high { background: #F0A040; color: #0A1628; }
.level-badge.medium { background: #2FA7D1; color: #fff; }
.level-badge.low { background: #3A5070; color: #8EA8C8; }
.status-badge.pending, .status-badge.assigned { background: rgba(240,160,64,0.2); color: #F0A040; }
.status-badge.in_progress { background: rgba(47,167,209,0.2); color: #2FA7D1; }
.status-badge.closed { background: rgba(64,201,160,0.2); color: #40C9A0; }
.status-badge.cancelled { background: rgba(128,128,128,0.2); color: #888; }

.order-title { color: #E8ECF1; font-size: 1em; margin-bottom: 6px; }
.order-meta { display: flex; gap: 20px; font-size: 0.8em; color: #5A7A9A; }

.modal-backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #0A1628; border: 1px solid #1E3A5F; border-radius: 8px; width: 700px; max-height: 80vh; overflow-y: auto; padding: 24px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; color: #2FA7D1; }
.close-btn { background: none; border: none; color: #8EA8C8; font-size: 1.5em; cursor: pointer; }
.field { margin-top: 14px; }
.field label { display: block; color: #2FA7D1; font-size: 0.8em; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.field p, .field ol { color: #A0B8D0; margin: 0; line-height: 1.6; }
.field .desc { white-space: pre-wrap; }
.safety-notes { background: rgba(232,85,85,0.08); border: 1px solid rgba(232,85,85,0.2); border-radius: 4px; padding: 10px; }
.safety-item { color: #E85555; font-size: 0.85em; padding: 2px 0; }

.status-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.status-btn { padding: 6px 14px; background: #1E3A5F; border: 1px solid #2FA7D1; color: #2FA7D1; border-radius: 4px; cursor: pointer; }
.status-btn:hover { background: #2FA7D1; color: #fff; }

.field input { padding: 8px 12px; background: #0D1F35; border: 1px solid #1E3A5F; color: #e0e0e0; border-radius: 4px; width: 200px; }
.small-btn { margin-left: 8px; padding: 6px 14px; background: #1E3A5F; border: 1px solid #2FA7D1; color: #2FA7D1; border-radius: 4px; cursor: pointer; }

.loading, .empty { text-align: center; padding: 40px; color: #5A7A9A; }
</style>
