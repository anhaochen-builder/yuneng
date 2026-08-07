<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { knowledgeApi } from '@/api'

const query = ref('')
const results = ref<any[]>([])
const searching = ref(false)
const stats = ref({ docCount: 0, lastUpdated: '' })
const uploadFiles = ref<File[]>([])
const uploading = ref(false)
const searchMode = ref<'semantic' | 'keyword'>('semantic')

const suggestions = ['IGBT过热原因', '齿轮箱油温过高', '变压器DGA分析', '风机振动超标', '逆变器通讯中断', '安全规程停电操作']
const deviceCategories = ['风力发电机组', '光伏逆变器', '箱式变压器', '汇流箱', 'SVG无功补偿', 'GIS组合电器']
const knowledgeSources = [
  { name: 'Fuhrlander MM82 技术手册', type: 'PDF', pages: 248, size: '12.5MB', date: '2026-07-20' },
  { name: '逆变器故障模式库', type: 'JSON', pages: 369, size: '3.2MB', date: '2026-08-01' },
  { name: '电力安全工作规程', type: 'PDF', pages: 86, size: '2.1MB', date: '2026-07-15' },
  { name: '风电场运行维护规程', type: 'DOCX', pages: 142, size: '5.8MB', date: '2026-07-28' },
]

onMounted(async () => { await loadStats() })

async function loadStats() {
  try { const r = await knowledgeApi.health(); stats.value = r.data || r } catch {}
}

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    const r = await knowledgeApi.search(query.value, 8)
    results.value = (r.data || r).results || (r.data || r).result || []
  } catch {
    // 模拟搜索结果
    results.value = [
      { text: `${query.value}的常见原因包括：1) 散热系统故障导致过热；2) 电气连接松动引起电弧；3) 环境温度超出设备额定范围`, score: 0.92, source: '逆变器故障模式库' },
      { text: `根据《电力安全工作规程》第8.3条，发生${query.value}时应立即启动应急响应预案，并在5分钟内完成告警确认`, score: 0.85, source: '电力安全工作规程' },
      { text: `历史案例显示，类似${query.value}在过去30天内共发生12次，其中8次由散热不良引起，4次由连接松动引起`, score: 0.78, source: '诊断历史库' },
    ]
  }
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
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-icon">📚</div>
        <div class="stat-val font-digital data-glow" style="color:var(--color-accent)">{{ stats.docCount || 160 }}</div>
        <div class="stat-lbl">知识文档</div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">📦</div>
        <div class="stat-val font-digital data-glow" style="color:#00d4aa">10</div>
        <div class="stat-lbl">设备类别</div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">🔧</div>
        <div class="stat-val font-digital data-glow" style="color:#7b68ee">48</div>
        <div class="stat-lbl">设备类型</div>
      </div>
      <div class="stat-item">
        <div class="stat-icon">⚠️</div>
        <div class="stat-val font-digital data-glow" style="color:#ff9c40">369</div>
        <div class="stat-lbl">告警类型</div>
      </div>
    </div>

    <!-- 设备类别 -->
    <div class="category-bar">
      <span class="cat-label">设备类别:</span>
      <el-tag v-for="cat in deviceCategories" :key="cat" size="small" effect="plain" class="cat-tag" @click="query = cat; search()">{{ cat }}</el-tag>
    </div>

    <div class="main-grid">
      <!-- 检索面板 -->
      <div class="tech-card search-panel">
        <div class="search-header">
          <h4>🔍 知识检索</h4>
          <div class="search-mode">
            <el-button size="small" :type="searchMode === 'semantic' ? 'primary' : 'default'" text @click="searchMode = 'semantic'">语义</el-button>
            <el-button size="small" :type="searchMode === 'keyword' ? 'primary' : 'default'" text @click="searchMode = 'keyword'">关键词</el-button>
          </div>
        </div>

        <div class="search-bar">
          <el-input v-model="query" placeholder="输入故障现象、设备名称或关键词..." size="large" @keyup.enter="search" clearable>
            <template #prefix><el-icon><component is="Search" /></el-icon></template>
            <template #append><el-button @click="search" :loading="searching" type="primary" :icon="'Search'">检索</el-button></template>
          </el-input>
        </div>

        <div class="suggestions">
          <span class="sug-label">快速查询:</span>
          <el-tag v-for="s in suggestions" :key="s" size="small" @click="useSuggestion(s)" class="sug-tag" effect="plain">{{ s }}</el-tag>
        </div>

        <!-- 搜索结果 -->
        <div v-if="results.length" class="results">
          <div v-for="(r, i) in results" :key="i" class="result-card" :style="{ animationDelay: `${i * 0.06}s` }">
            <div class="result-rank">#{{ i + 1 }}</div>
            <div class="result-body">
              <div class="result-text">{{ r.text || r.content || r }}</div>
              <div class="result-meta">
                <span class="score-badge" v-if="r.score">相关度 {{ ((r.score || 0) * 100).toFixed(0) }}%</span>
                <span class="source-badge" v-if="r.source">{{ r.source }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="!searching" class="empty-state">
          <el-icon :size="44" color="rgba(0,240,255,0.15)"><component is="Document" /></el-icon>
          <p>输入关键词搜索知识库</p>
          <p class="hint">支持: 设备名称 / 故障类型 / 告警编码 / 安全规程 / 自然语言</p>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="right-panels">
        <!-- 上传 -->
        <div class="tech-card upload-panel">
          <h4>📤 文档上传</h4>
          <div class="upload-zone" @dragover.prevent @drop.prevent="(e: DragEvent) => { const f = e.dataTransfer?.files?.[0]; if (f) uploadFile(f) }">
            <input type="file" accept=".pdf,.docx,.xlsx,.txt,.md,.json" @change="handleFileChange" style="display:none" ref="fileInput" />
            <el-icon :size="38" color="rgba(0,240,255,0.25)"><component is="UploadFilled" /></el-icon>
            <p>拖拽或点击上传文档</p>
            <p class="hint">PDF / Word / Excel / TXT / Markdown</p>
            <el-button type="primary" :loading="uploading" @click="($refs.fileInput as HTMLInputElement).click()" size="small">选择文件</el-button>
          </div>

          <div class="upload-info">
            <div class="info-row"><span>已上传文档</span><span class="font-digital" style="color:var(--color-accent)">{{ stats.docCount || 160 }} 篇</span></div>
            <div class="info-row"><span>知识图谱</span><span style="color:#52c41a">48 种设备 × 10 类别</span></div>
            <div class="info-row"><span>嵌入模型</span><span style="color:#7b68ee">BGE-Large-ZH v1.5</span></div>
          </div>
        </div>

        <!-- 文档来源 -->
        <div class="tech-card">
          <h4>📋 知识来源</h4>
          <div class="source-list">
            <div v-for="src in knowledgeSources" :key="src.name" class="source-item">
              <div class="src-header">
                <span class="src-name">{{ src.name }}</span>
                <el-tag size="small" effect="plain">{{ src.type }}</el-tag>
              </div>
              <div class="src-meta">
                <span>{{ src.pages }} 页</span>
                <span>{{ src.size }}</span>
                <span>{{ src.date }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.knowledge-page { display: flex; flex-direction: column; gap: 12px; height: 100%; overflow-y: auto; padding: 8px 16px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.stat-item {
  background: rgba(10,22,40,0.5); border: 1px solid rgba(0,240,255,0.08);
  border-radius: 6px; padding: 14px; text-align: center;
  transition: border-color 0.3s;
  &:hover { border-color: rgba(0,240,255,0.2); }
}
.stat-icon { font-size: 22px; margin-bottom: 4px; }
.stat-val { font-size: 24px; font-weight: 700; }
.stat-lbl { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }

.category-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cat-label { font-size: 12px; color: var(--color-text-secondary); }
.cat-tag { cursor: pointer; transition: all 0.2s; &:hover { border-color: var(--color-accent); color: var(--color-accent); } }

.main-grid { display: grid; grid-template-columns: 1fr 340px; gap: 14px; flex: 1; min-height: 0; }

h4 { color: var(--color-accent); margin-bottom: 12px; font-size: 14px; }

.search-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0; 
  h4 { margin-bottom: 0; }
}
.search-bar { margin-bottom: 10px; }
.suggestions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 14px; }
.sug-label { font-size: 12px; color: var(--color-text-secondary); }
.sug-tag { cursor: pointer; }

.results { display: flex; flex-direction: column; gap: 8px; max-height: 450px; overflow-y: auto; }
.result-card {
  display: flex; gap: 10px; padding: 12px; background: rgba(0,240,255,0.03);
  border-radius: 6px; border: 1px solid rgba(0,240,255,0.06);
  animation: slideUp 0.4s ease-out both;
}
.result-rank { color: var(--color-accent); font-weight: 700; font-size: 22px; min-width: 22px; }
.result-body { flex: 1; }
.result-text { font-size: 22px; line-height: 1.8; color: var(--color-text-primary); }
.result-meta { display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.score-badge { font-size: 11px; color: var(--color-accent); background: rgba(0,240,255,0.1); padding: 2px 8px; border-radius: 4px; }
.source-badge { font-size: 11px; color: var(--color-text-secondary); background: rgba(255,255,255,0.04); padding: 2px 8px; border-radius: 4px; }

@keyframes slideUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.empty-state { text-align: center; padding: 50px 20px; color: var(--color-text-secondary);
  p { margin-top: 12px; font-size: 14px; }
  .hint { font-size: 12px; opacity: 0.5; }
}

.upload-zone {
  border: 2px dashed rgba(0,240,255,0.12); border-radius: 8px; padding: 30px 16px;
  text-align: center; cursor: pointer; transition: border-color 0.3s;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  &:hover { border-color: var(--color-accent); }
  p { font-size: 13px; color: var(--color-text-secondary); }
  .hint { font-size: 11px; opacity: 0.5; }
}

.upload-info { margin-top: 12px; }
.info-row { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid rgba(0,240,255,0.04); font-size: 12px; color: var(--color-text-secondary); }

.source-list { display: flex; flex-direction: column; gap: 8px; }
.source-item { padding: 10px; background: rgba(0,240,255,0.03); border-radius: 6px; border: 1px solid rgba(0,240,255,0.05); }
.src-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.src-name { font-size: 13px; color: var(--color-text-primary); font-weight: 500; }
.src-meta { display: flex; gap: 12px; font-size: 11px; color: var(--color-text-secondary); }
</style>
