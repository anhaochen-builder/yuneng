<script setup lang="ts">
import { ref, computed } from 'vue'
import { diagnoseApi } from '@/api'

interface ReportItem {
  task_id: string; device_id: string; device_name: string; device_type: string
  symptoms: string; root_cause: string; confidence: number; risk_level: string
  created_at: string; status: string
}

const reports = ref<ReportItem[]>([])
const loading = ref(false)
const searchText = ref('')
const filterDevice = ref('')
const filterRisk = ref('all')
const filterDate = ref('')
const selectedReport = ref<ReportItem | null>(null)
const showDetail = ref(false)

const mockReports: ReportItem[] = [
  { task_id:'DX-20260804-001',device_id:'WT001',device_name:'1号风机',device_type:'风电机组',symptoms:'齿轮箱油温异常升高至82°C，振动值超标',root_cause:'齿轮箱润滑油劣化，轴承磨损加剧',confidence:0.88,risk_level:'HIGH',created_at:'2026-08-04 14:30',status:'已完成'},
  { task_id:'DX-20260804-002',device_id:'INV003',device_name:'3号逆变器',device_type:'光伏逆变器',symptoms:'通讯中断，后台报ALM-001告警',root_cause:'IGBT模块过热导致保护性停机，通讯模块因供电异常中断',confidence:0.92,risk_level:'CRITICAL',created_at:'2026-08-04 13:15',status:'已完成'},
  { task_id:'DX-20260804-003',device_id:'WT002',device_name:'2号风机',device_type:'风电机组',symptoms:'振动超标停机，风速28.5m/s',root_cause:'瞬时大风导致叶片受力失衡，非机械故障',confidence:0.85,risk_level:'MEDIUM',created_at:'2026-08-04 11:20',status:'已完成'},
  { task_id:'DX-20260804-004',device_id:'TRA001',device_name:'1号主变',device_type:'变压器',symptoms:'油温持续升高至88°C，DGA氢气含量150ppm',root_cause:'冷却系统风扇效率下降，建议检修散热器',confidence:0.78,risk_level:'MEDIUM',created_at:'2026-08-04 10:05',status:'已完成'},
  { task_id:'DX-20260803-008',device_id:'INV001',device_name:'1号逆变器',device_type:'光伏逆变器',symptoms:'直流侧绝缘阻抗降低至250kΩ',root_cause:'MC4接头密封不良进水，组件绝缘老化',confidence:0.91,risk_level:'HIGH',created_at:'2026-08-03 16:40',status:'已完成'},
  { task_id:'DX-20260803-007',device_id:'SVG001',device_name:'SVG补偿器',device_type:'无功补偿',symptoms:'IGBT模块过温，功率模块故障报警',root_cause:'散热风道堵塞，滤网积尘严重',confidence:0.86,risk_level:'HIGH',created_at:'2026-08-03 14:20',status:'已完成'},
  { task_id:'DX-20260803-005',device_id:'BAT001',device_name:'1号储能舱',device_type:'储能系统',symptoms:'电芯电压不均衡，SOC异常跳跃',root_cause:'BMS采集模块故障，电芯容量衰减不一致',confidence:0.72,risk_level:'MEDIUM',created_at:'2026-08-03 09:50',status:'待审核'},
  { task_id:'DX-20260802-012',device_id:'WT004',device_name:'4号风机',device_type:'风电机组',symptoms:'发电机轴承温度持续升高至95°C',root_cause:'轴承润滑脂不足，冷却风道局部堵塞',confidence:0.90,risk_level:'CRITICAL',created_at:'2026-08-02 18:10',status:'已完成'},
  { task_id:'DX-20260802-010',device_id:'PROT01',device_name:'线路保护A',device_type:'保护装置',symptoms:'差动保护误动作，采样值异常',root_cause:'CT二次回路接触不良，光纤通道误码率高',confidence:0.83,risk_level:'HIGH',created_at:'2026-08-02 15:30',status:'已完成'},
  { task_id:'DX-20260801-003',device_id:'INV002',device_name:'2号逆变器',device_type:'光伏逆变器',symptoms:'输出功率异常波动，电网电压频率超限',root_cause:'电网侧电压波动超出LVRT范围，逆变器自动降功率',confidence:0.80,risk_level:'MEDIUM',created_at:'2026-08-01 11:00',status:'已完成'},
  { task_id:'DX-20260801-001',device_id:'WT003',device_name:'3号风机',device_type:'风电机组',symptoms:'偏航系统异响，偏航角度偏差>5°',root_cause:'偏航制动器摩擦片磨损超标，偏航齿轮啮合间隙过大',confidence:0.87,risk_level:'HIGH',created_at:'2026-08-01 08:45',status:'已完成'},
  { task_id:'DX-20260731-015',device_id:'TRA002',device_name:'2号箱变',device_type:'变压器',symptoms:'铁芯接地电流增大至120mA',root_cause:'铁芯多点接地，变压器内部绝缘局部劣化',confidence:0.75,risk_level:'MEDIUM',created_at:'2026-07-31 20:30',status:'已完成'},
]

const stats = computed(() => ({
  total: filteredReports.value.length,
  critical: filteredReports.value.filter(r => r.risk_level === 'CRITICAL').length,
  high: filteredReports.value.filter(r => r.risk_level === 'HIGH').length,
  medium: filteredReports.value.filter(r => r.risk_level === 'MEDIUM').length,
  avgConfidence: filteredReports.value.length > 0
    ? (filteredReports.value.reduce((s, r) => s + r.confidence, 0) / filteredReports.value.length * 100).toFixed(0)
    : 0,
}))

const filteredReports = computed(() => {
  let list = reports.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(r => r.task_id.toLowerCase().includes(q) || r.device_id.toLowerCase().includes(q) || r.device_name.includes(q) || r.symptoms.includes(q))
  }
  if (filterDevice.value) list = list.filter(r => r.device_id === filterDevice.value || r.device_type === filterDevice.value)
  if (filterRisk.value !== 'all') list = list.filter(r => r.risk_level === filterRisk.value)
  if (filterDate.value) list = list.filter(r => r.created_at.startsWith(filterDate.value))
  return list.sort((a, b) => b.created_at.localeCompare(a.created_at))
})

const deviceTypes = computed(() => [...new Set(reports.value.map(r => r.device_type))])
const deviceIds = computed(() => [...new Set(reports.value.map(r => r.device_id))])

function loadReports() {
  loading.value = true
  // 实际对接: const r = await diagnoseApi.history(); reports.value = r.data || mockReports
  reports.value = mockReports
  loading.value = false
}

function viewReport(report: ReportItem) { selectedReport.value = report; showDetail.value = true }

function exportCSV() {
  const headers = '任务ID,设备ID,设备名称,设备类型,故障描述,根因,置信度,风险等级,时间,状态\n'
  const rows = filteredReports.value.map(r => `${r.task_id},${r.device_id},${r.device_name},${r.device_type},"${r.symptoms}","${r.root_cause}",${(r.confidence*100).toFixed(0)}%,${r.risk_level},${r.created_at},${r.status}`).join('\n')
  const blob = new Blob(['\uFEFF' + headers + rows], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = `驭能诊断报告_${new Date().toISOString().slice(0,10)}.csv`; a.click()
  URL.revokeObjectURL(url)
}

function exportJSON() {
  const data = filteredReports.value.map(r => ({
    task_id: r.task_id, device_id: r.device_id, device_name: r.device_name,
    device_type: r.device_type, symptoms: r.symptoms, root_cause: r.root_cause,
    confidence: r.confidence, risk_level: r.risk_level, created_at: r.created_at,
  }))
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = `驭能诊断报告_${new Date().toISOString().slice(0,10)}.json`; a.click()
  URL.revokeObjectURL(url)
}

function getRiskType(level: string) { return level === 'CRITICAL' ? 'danger' : level === 'HIGH' ? 'warning' : level === 'MEDIUM' ? 'primary' : 'info' }
function getConfColor(c: number) { return c >= 0.85 ? '#52c41a' : c >= 0.7 ? '#ff9c40' : '#ff4d4f' }

loadReports()
</script>

<template>
  <div class="report-page animate-fade-in">
    <div class="stats-bar">
      <div class="stat-chip" v-for="s in [
        { label:'报告总数', value:stats.total, color:'var(--color-accent)' },
        { label:'CRITICAL', value:stats.critical, color:'#ff4d4f' },
        { label:'HIGH', value:stats.high, color:'#ff9c40' },
        { label:'MEDIUM', value:stats.medium, color:'var(--color-accent)' },
        { label:'平均置信度', value:stats.avgConfidence + '%', color:'#52c41a' },
      ]" :key="s.label">
        <span class="sc-val font-digital" :style="{color:s.color}">{{ s.value }}</span>
        <span class="sc-lbl">{{ s.label }}</span>
      </div>
      <div class="export-btns">
        <el-button size="small" @click="exportCSV" icon="Download">导出 CSV</el-button>
        <el-button size="small" @click="exportJSON" icon="Download">导出 JSON</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchText" placeholder="搜索任务ID / 设备 / 故障描述..." size="small" clearable style="width:300px" />
      <el-select v-model="filterRisk" size="small" style="width:120px" placeholder="风险等级">
        <el-option label="全部等级" value="all" />
        <el-option label="CRITICAL" value="CRITICAL" />
        <el-option label="HIGH" value="HIGH" />
        <el-option label="MEDIUM" value="MEDIUM" />
      </el-select>
      <el-select v-model="filterDevice" size="small" style="width:140px" placeholder="设备类型" clearable>
        <el-option v-for="t in deviceTypes" :key="t" :label="t" :value="t" />
      </el-select>
      <el-date-picker v-model="filterDate" type="date" size="small" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:150px" />
      <span class="filter-count">共 {{ filteredReports.length }} 条报告</span>
    </div>

    <div class="report-table">
      <el-table :data="filteredReports" size="small" stripe highlight-current-row v-loading="loading"
        @row-click="(row: any) => viewReport(row)" max-height="calc(100vh - 240px)">
        <el-table-column prop="task_id" label="任务ID" width="180" />
        <el-table-column prop="device_id" label="设备" width="100" />
        <el-table-column prop="device_name" label="名称" width="100" />
        <el-table-column prop="device_type" label="类型" width="100" />
        <el-table-column prop="symptoms" label="故障描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row: r }"><el-tag size="small" :type="getRiskType(r.risk_level)">{{ r.risk_level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="90">
          <template #default="{ row: r }"><span class="font-digital" :style="{color:getConfColor(r.confidence)}">{{ (r.confidence*100).toFixed(0) }}%</span></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row: r }"><el-tag size="small" :type="r.status === '已完成' ? 'success' : 'warning'">{{ r.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="140" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row: r }"><el-button size="small" text type="primary" @click.stop="viewReport(r)">详情</el-button></template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDetail" title="诊断报告详情" width="700px">
      <div v-if="selectedReport" class="report-detail">
        <div class="rd-header">
          <span class="rd-id font-digital">{{ selectedReport.task_id }}</span>
          <el-tag size="large" :type="getRiskType(selectedReport.risk_level)">{{ selectedReport.risk_level }}</el-tag>
        </div>
        <div class="rd-grid">
          <div class="rd-item"><span class="rd-label">设备</span><span>{{ selectedReport.device_name }} ({{ selectedReport.device_id }})</span></div>
          <div class="rd-item"><span class="rd-label">设备类型</span><span>{{ selectedReport.device_type }}</span></div>
          <div class="rd-item"><span class="rd-label">时间</span><span>{{ selectedReport.created_at }}</span></div>
          <div class="rd-item"><span class="rd-label">置信度</span><span class="font-digital" :style="{color:getConfColor(selectedReport.confidence)}">{{ (selectedReport.confidence*100).toFixed(0) }}%</span></div>
          <div class="rd-item"><span class="rd-label">状态</span><el-tag size="small" :type="selectedReport.status === '已完成' ? 'success' : 'warning'">{{ selectedReport.status }}</el-tag></div>
        </div>
        <div class="rd-section">
          <div class="rd-section-title">故障描述</div>
          <div class="rd-section-body">{{ selectedReport.symptoms }}</div>
        </div>
        <div class="rd-section">
          <div class="rd-section-title">根因分析</div>
          <div class="rd-section-body">{{ selectedReport.root_cause }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
        <el-button type="primary" @click="exportJSON">导出 JSON</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.report-page { display: flex; flex-direction: column; gap: 12px; height: calc(100vh - 130px); padding: 8px 16px; overflow: hidden; }

.stats-bar { display: flex; gap: 12px; align-items: center; }
.stat-chip { padding: 8px 16px; background: rgba(10,22,40,0.5); border: 1px solid rgba(0,240,255,0.08); border-radius: 6px; text-align: center; min-width: 80px; }
.sc-val { font-size: 20px; font-weight: 700; display: block; }
.sc-lbl { font-size: 11px; color: var(--color-text-secondary); }
.export-btns { margin-left: auto; display: flex; gap: 8px; }

.filter-bar { display: flex; gap: 10px; align-items: center; }
.filter-count { font-size: 12px; color: var(--color-text-secondary); margin-left: auto; }

.report-detail { display: flex; flex-direction: column; gap: 14px; }
.rd-header { display: flex; justify-content: space-between; align-items: center; }
.rd-id { font-size: 16px; color: var(--color-accent); }
.rd-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.rd-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(0,240,255,0.05); font-size: 13px; }
.rd-label { color: var(--color-text-secondary); }
.rd-section { margin-top: 4px; }
.rd-section-title { font-size: 13px; color: var(--color-accent); margin-bottom: 6px; font-weight: 600; }
.rd-section-body { font-size: 13px; color: var(--color-text-secondary); line-height: 1.7; padding: 10px; background: rgba(0,240,255,0.03); border-radius: 6px; }
</style>
