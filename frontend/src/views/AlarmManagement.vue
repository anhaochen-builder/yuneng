<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { alarmApi } from '@/api'
import AlarmPieChart from '@/components/charts/AlarmPieChart.vue'

const alarms = ref<any[]>([])
const alarmForm = ref({
  alarm_id: '', device_id: '', device_type: '逆变器', alarm_type: '通讯中断',
  alarm_level: 'high', alarm_message: '', current_value: '', threshold: '', auto_diagnose: true,
})
const submitting = ref(false)
const diagResult = ref<any>(null)
const filterLevel = ref<string>('all')
const showForm = ref(false)

onMounted(async () => {
  try { await alarmApi.health() } catch {}
})

const filteredAlarms = computed(() => {
  if (filterLevel.value === 'all') return alarms.value
  return alarms.value.filter((a: any) => a.risk_level === filterLevel.value || a.levelDisplay === filterLevel.value)
})

const alarmTypeData = computed(() => {
  const types: Record<string, number> = {}
  alarms.value.forEach((a: any) => {
    const t = a.alarm_type || '其他'
    types[t] = (types[t] || 0) + 1
  })
  return Object.entries(types).map(([type, count]) => ({ type, count }))
})

async function submitAlarm() {
  submitting.value = true
  try {
    const r = await alarmApi.receive({
      alarm_id: alarmForm.value.alarm_id || `ALM-${Date.now().toString(36).toUpperCase()}`,
      device_id: alarmForm.value.device_id,
      device_type: alarmForm.value.device_type,
      alarm_type: alarmForm.value.alarm_type,
      level: alarmForm.value.alarm_level,
      message: alarmForm.value.alarm_message || `${alarmForm.value.device_type} ${alarmForm.value.alarm_type}`,
      current_value: alarmForm.value.current_value,
      threshold: alarmForm.value.threshold,
      auto_diagnose: alarmForm.value.auto_diagnose,
    })
    const data = r.data || r
    alarms.value.unshift({ ...data, time: new Date().toLocaleTimeString(), id: Date.now() })
    if (data.report) diagResult.value = data
    ElMessage.success('告警已接收' + (data.status === 'DIAGNOSED' ? '并自动诊断完成' : ''))
    // 重置表单
    alarmForm.value.alarm_id = ''
    alarmForm.value.alarm_message = ''
    alarmForm.value.current_value = ''
    alarmForm.value.threshold = ''
  } catch { ElMessage.error('告警提交失败') }
  submitting.value = false
}

function clearAlarms() { alarms.value = []; diagResult.value = null }

const quickAlarms = [
  { label: '逆变器通讯中断', alarm_type: '通讯中断', device_type: '逆变器', level: 'critical', msg: '3号逆变器通讯中断，SCADA后台显示离线状态已持续3分钟' },
  { label: '风机振动超标', alarm_type: '振动超标', device_type: '风机', level: 'high', msg: '1号风机振动值超出阈值，当前值12.5mm/s，阈值为8mm/s' },
  { label: '变压器油温异常', alarm_type: '温度异常', device_type: '变压器', level: 'high', msg: '1号主变油温持续上升至85°C，接近报警阈值90°C' },
]
</script>

<template>
  <div class="alarm-page animate-fade-in">
    <!-- 统计概览 -->
    <div class="alarm-stats">
      <div class="as-card critical"><span class="as-num font-digital">{{ alarms.filter((a:any)=>a.risk_level==='CRITICAL').length }}</span><span class="as-label">严重告警</span></div>
      <div class="as-card high"><span class="as-num font-digital">{{ alarms.filter((a:any)=>a.risk_level==='HIGH').length }}</span><span class="as-label">高危告警</span></div>
      <div class="as-card medium"><span class="as-num font-digital">{{ alarms.filter((a:any)=>a.risk_level==='MEDIUM').length }}</span><span class="as-label">中危告警</span></div>
      <div class="as-card total"><span class="as-num font-digital">{{ alarms.length }}</span><span class="as-label">告警总数</span></div>
    </div>

    <div class="grid-2col">
      <!-- 告警表单 -->
      <div class="tech-card">
        <div class="card-header">
          <h4>🚨 告警接收</h4>
          <el-button size="small" text @click="showForm = !showForm">{{ showForm ? '收起' : '展开' }}</el-button>
        </div>

        <!-- 快速告警 -->
        <div class="quick-alarms">
          <el-tag v-for="qa in quickAlarms" :key="qa.label" size="small" effect="plain" 
            @click="alarmForm.alarm_type = qa.alarm_type; alarmForm.device_type = qa.device_type; alarmForm.alarm_level = qa.level; alarmForm.alarm_message = qa.msg; showForm = true"
            class="quick-tag">
            {{ qa.label }}
          </el-tag>
        </div>

        <el-form v-if="showForm" :model="alarmForm" label-width="75px" size="small" class="alarm-form">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="告警编号"><el-input v-model="alarmForm.alarm_id" placeholder="留空自动生成" /></el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="设备ID"><el-input v-model="alarmForm.device_id" placeholder="如: INV003" /></el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="设备类型">
                <el-select v-model="alarmForm.device_type">
                  <el-option label="逆变器" value="逆变器" />
                  <el-option label="风机" value="风机" />
                  <el-option label="变压器" value="变压器" />
                  <el-option label="汇流箱" value="汇流箱" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="告警类型"><el-input v-model="alarmForm.alarm_type" placeholder="通讯中断" /></el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="级别">
                <el-select v-model="alarmForm.alarm_level">
                  <el-option label="CRITICAL" value="critical" />
                  <el-option label="HIGH" value="high" />
                  <el-option label="MEDIUM" value="medium" />
                  <el-option label="LOW" value="low" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="当前值"><el-input v-model="alarmForm.current_value" placeholder="如: 85°C" /></el-form-item>
          <el-form-item label="阈值"><el-input v-model="alarmForm.threshold" placeholder="如: 75°C" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="alarmForm.alarm_message" type="textarea" rows="2" placeholder="详细描述故障现象..." /></el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="自动诊断"><el-switch v-model="alarmForm.auto_diagnose" /></el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item>
                <el-button type="primary" @click="submitAlarm" :loading="submitting" style="width:100%">
                  {{ submitting ? '提交中...' : '🚨 提交告警' }}
                </el-button>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>

      <!-- 告警记录 -->
      <div class="tech-card">
        <div class="card-header">
          <h4>📋 告警记录</h4>
          <div class="filter-btns">
            <el-button size="small" text :type="filterLevel==='all'?'primary':'default'" @click="filterLevel='all'">全部</el-button>
            <el-button size="small" text :type="filterLevel==='CRITICAL'?'danger':'default'" @click="filterLevel='CRITICAL'">严重</el-button>
            <el-button size="small" text :type="filterLevel==='HIGH'?'warning':'default'" @click="filterLevel='HIGH'">高危</el-button>
            <el-button size="small" text @click="clearAlarms">清空</el-button>
          </div>
        </div>

        <div v-if="filteredAlarms.length" class="alarm-list">
          <div v-for="a in filteredAlarms" :key="a.id || a.task_id" class="alarm-item" :class="(a.risk_level || a.levelDisplay || '').toLowerCase()">
            <div class="alarm-header">
              <el-tag size="small" :type="(a.risk_level||'') === 'CRITICAL' ? 'danger' : (a.risk_level||'') === 'HIGH' ? 'warning' : 'info'" effect="dark">
                {{ a.risk_level || a.levelDisplay || '-' }}
              </el-tag>
              <span class="alarm-id font-digital">{{ a.alarm_id || a.task_id || '-' }}</span>
              <span class="alarm-type">{{ a.alarm_type || '-' }}</span>
              <span class="alarm-time">{{ a.time }}</span>
            </div>
            <div class="alarm-detail">{{ a.message || a.report?.slice(0, 200) || a.raw?.slice(0, 150) }}</div>
          </div>
        </div>

        <div v-else class="empty-state">
          <el-icon :size="40" color="rgba(0,240,255,0.15)"><component is="Bell" /></el-icon>
          <p>暂无告警记录</p>
          <p class="hint">提交告警或等待 SCADA 推送</p>
        </div>
      </div>
    </div>

    <!-- 告警分布图 -->
    <div class="tech-card" v-if="alarmTypeData.length">
      <h4>📊 告警类型分布</h4>
      <AlarmPieChart :data="alarmTypeData" />
    </div>

    <!-- 诊断结果 -->
    <div class="tech-card" v-if="diagResult" style="border-color:rgba(0,240,255,0.3)">
      <h4>🔧 自动诊断结果</h4>
      <div class="diag-result">
        <div v-if="diagResult.root_causes?.length">
          <div v-for="(c, i) in diagResult.root_causes" :key="i" class="cause-row">
            <span class="cause-rank">#{{ Number(i) + 1 }}</span>
            <span>{{ c.cause }}</span>
            <el-tag size="small" :type="(c.probability||0)>0.7?'danger':(c.probability||0)>0.4?'warning':'success'">
              {{ ((c.probability || 0) * 100).toFixed(0) }}%
            </el-tag>
          </div>
        </div>
        <div v-else class="empty-state">诊断中...</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.alarm-page { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.alarm-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.as-card { padding: 16px; text-align: center; border-radius: 6px; border: 1px solid; }
.as-card.critical { border-color: rgba(255,77,79,0.3); background: rgba(255,77,79,0.06); }
.as-card.high { border-color: rgba(255,156,64,0.3); background: rgba(255,156,64,0.06); }
.as-card.medium { border-color: rgba(0,240,255,0.2); background: rgba(0,240,255,0.04); }
.as-card.total { border-color: rgba(0,240,255,0.15); background: rgba(0,240,255,0.03); }
.as-num { font-size: 28px; font-weight: 700; display: block; }
.as-card.critical .as-num { color: #ff4d4f; }
.as-card.high .as-num { color: #ff9c40; }
.as-card.medium .as-num { color: var(--color-accent); }
.as-card.total .as-num { color: #fff; }
.as-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }

.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.card-header h4 { color: var(--color-accent); font-size: 14px; margin: 0; }

.quick-alarms { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.quick-tag { cursor: pointer; transition: all 0.2s; &:hover { border-color: var(--color-accent); color: var(--color-accent); } }

.alarm-form { margin-top: 8px; }

.filter-btns { display: flex; gap: 2px; }

.alarm-list { max-height: 400px; overflow-y: auto; }
.alarm-item { padding: 10px 12px; border-bottom: 1px solid rgba(0,240,255,0.05); font-size: 13px;
  &.critical { border-left: 3px solid #ff4d4f; }
  &.high { border-left: 3px solid #ff9c40; }
  &.medium { border-left: 3px solid var(--color-accent); }
}
.alarm-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.alarm-id { font-size: 11px; color: var(--color-accent); }
.alarm-type { font-size: 12px; color: var(--color-text-secondary); }
.alarm-time { font-size: 11px; color: var(--color-text-secondary); margin-left: auto; }
.alarm-detail { color: var(--color-text-secondary); font-size: 12px; line-height: 1.5; margin-top: 4px; }

.diag-result { padding: 8px 0; }
.cause-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid rgba(0,240,255,0.05); }
.cause-rank { font-weight: 700; color: var(--color-accent); }

.empty-state { text-align: center; color: var(--color-text-secondary); padding: 32px;
  p { margin-top: 10px; font-size: 13px; }
  .hint { font-size: 11px; opacity: 0.5; }
}

h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }
</style>
