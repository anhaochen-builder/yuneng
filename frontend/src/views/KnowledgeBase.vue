<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { knowledgeApi } from '@/api'

const query = ref('')
const results = ref<any[]>([])
const searching = ref(false)
const stats = ref({ docCount: 0, lastUpdated: '' })
const uploadFiles = ref<File[]>([])
const uploading = ref(false)

const suggestions = ['IGBT过热原因', '齿轮箱油温过高', '变压器DGA分析', '风机振动超标', '逆变器通讯中断', '安全规程停电操作']

onMounted(async () => {
  await loadStats()
})

async function loadStats() {
  try { const r = await knowledgeApi.health(); stats.value = r.data || r } catch {}
}

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    const r = await knowledgeApi.search(query.value, 8)
    results.value = (r.data || r).results || (r.data || r).result || []
  } catch { ElMessage.error('检索失败') }
  searching.value = false
}

function useSuggestion(s: string) { query.value = s; search() }

async function uploadFile(file: File) {
  uploading.value = true
  try {
    const fd = new FormData(); fd.append('file', file)
    await knowledgeApi.upload(fd)
    ElMessage.success(`已上传: ${file.name}`)
    await loadStats()
  } catch { ElMessage.error('上传失败') }
  uploading.value = false
}

function handleFileChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (files) { for (const f of files) uploadFile(f) }
}
</script>

<template>
  <div class="knowledge-page animate-fade-in">
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-val font-digital data-glow" style="color:var(--color-accent)">{{ stats.docCount || 160 }}</div>
        <div class="stat-lbl">知识文档</div>
      </div>
      <div class="stat-item">
        <div class="stat-val font-digital data-glow" style="color:#00d4aa">10</div>
        <div class="stat-lbl">设备类别</div>
      </div>
      <div class="stat-item">
        <div class="stat-val font-digital data-glow" style="color:#7b68ee">48</div>
        <div class="stat-lbl">设备类型</div>
      </div>
      <div class="stat-item">
        <div class="stat-val font-digital data-glow" style="color:#ff9c40">369</div>
        <div class="stat-lbl">真实告警类型</div>
      </div>
    </div>

    <div class="main-grid">
      <div class="tech-card search-panel">
        <h4>🔍 知识检索</h4>
        <div class="search-bar">
          <el-input v-model="query" placeholder="输入故障现象、设备名称或关键词..." size="large" @keyup.enter="search" clearable>
            <template #prepend><el-icon><component is="Search" /></el-icon></template>
            <template #append><el-button @click="search" :loading="searching" type="primary">检索</el-button></template>
          </el-input>
        </div>
        <div class="suggestions">
          <span class="sug-label">快速查询:</span>
          <el-tag v-for="s in suggestions" :key="s" size="small" @click="useSuggestion(s)" class="sug-tag" effect="plain">{{ s }}</el-tag>
        </div>

        <div v-if="results.length" class="results">
          <div v-for="(r, i) in results" :key="i" class="result-card animate-slide-up" :style="{ animationDelay: `${i * 0.05}s` }">
            <div class="result-rank">#{{ i + 1 }}</div>
            <div class="result-body">
              <div class="result-text">{{ r.text || r.content || r }}</div>
              <div class="result-meta" v-if="r.score">
                <span class="score-badge">相关度 {{ ((typeof r.score === 'number' ? r.score : 0.5) * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="!searching" class="empty-state">
          <el-icon :size="40" color="rgba(0,240,255,0.2)"><component is="Document" /></el-icon>
          <p>输入关键词搜索知识库</p>
          <p class="hint">支持: 设备名称、故障类型、告警编码、安全规程</p>
        </div>
      </div>

      <div class="tech-card upload-panel">
        <h4>📤 文档上传</h4>
        <div class="upload-zone" @dragover.prevent @drop.prevent="(e: DragEvent) => { const f = e.dataTransfer?.files?.[0]; if (f) uploadFile(f) }">
          <input type="file" accept=".pdf,.docx,.xlsx,.txt,.md" @change="handleFileChange" style="display:none" ref="fileInput" />
          <el-icon :size="36" color="rgba(0,240,255,0.3)"><component is="UploadFilled" /></el-icon>
          <p>拖拽或点击上传文档</p>
          <p class="hint">支持 PDF / Word / Excel / TXT / Markdown</p>
          <el-button type="primary" :loading="uploading" @click="($refs.fileInput as HTMLInputElement).click()">选择文件</el-button>
        </div>
        <div class="upload-info">
          <div class="info-row"><span>已上传文档</span><span class="font-digital" style="color:var(--color-accent)">{{ stats.docCount || 0 }} 篇</span></div>
          <div class="info-row"><span>知识图谱</span><span style="color:#52c41a">48 种设备 × 10 类别</span></div>
          <div class="info-row"><span>文档来源</span><span>Fuhrlander实测 + 通用安规</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.knowledge-page { display: flex; flex-direction: column; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-item { background: rgba(10,22,40,0.7); border: 1px solid rgba(0,240,255,0.1); border-radius: 6px; padding: 16px; text-align: center; }
.stat-val { font-size: 26px; font-weight: 700; }
.stat-lbl { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.main-grid { display: grid; grid-template-columns: 1fr 360px; gap: 16px; }
h4 { color: var(--color-accent); margin-bottom: 14px; font-size: 14px; }
.search-bar { margin-bottom: 12px; }
.suggestions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 16px; }
.sug-label { font-size: 12px; color: var(--color-text-secondary); }
.sug-tag { cursor: pointer; }
.results { display: flex; flex-direction: column; gap: 8px; max-height: 500px; overflow-y: auto; }
.result-card { display: flex; gap: 10px; padding: 12px 14px; background: rgba(0,240,255,0.03); border-radius: 6px; border: 1px solid rgba(0,240,255,0.06); }
.result-rank { color: var(--color-accent); font-weight: 700; font-size: 13px; min-width: 24px; }
.result-body { flex: 1; }
.result-text { font-size: 13px; line-height: 1.7; color: var(--color-text-primary); }
.result-meta { margin-top: 6px; }
.score-badge { font-size: 11px; color: var(--color-accent); background: var(--color-accent-dim); padding: 2px 8px; border-radius: 4px; }
.empty-state { text-align: center; padding: 60px 20px; color: var(--color-text-secondary);
  p { margin-top: 12px; }
  .hint { font-size: 12px; opacity: 0.6; }
}
.upload-zone { border: 2px dashed rgba(0,240,255,0.15); border-radius: 8px; padding: 40px 20px; text-align: center; cursor: pointer; transition: border-color 0.3s; display: flex; flex-direction: column; align-items: center; gap: 10px;
  &:hover { border-color: var(--color-accent); }
  p { font-size: 13px; color: var(--color-text-secondary); }
  .hint { font-size: 11px; opacity: 0.6; }
}
.upload-info { margin-top: 16px; }
.info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(0,240,255,0.05); font-size: 13px; color: var(--color-text-secondary); }
</style>
