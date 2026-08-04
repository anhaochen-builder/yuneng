<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = withDefaults(defineProps<{
  imageUrl?: string
  annotations?: Array<{ type: string; area: string; description: string; temp?: number; x?: number; y?: number }>
  mode?: 'thermal' | 'visible' | 'spectrum'
}>(), { mode: 'thermal' })

const activeTab = ref(props.mode)
const imageFile = ref<File | null>(null)
const imagePreview = ref(props.imageUrl || '')
const isDragging = ref(false)
const marks = ref<Array<{ x: number; y: number; label: string; color: string }>>([])

const mockAnnotations = [
  { type: '热点区域', area: 'IGBT模块 A相', description: '温度异常85.3°C，比周围高15°C', temp: 85.3, x: 35, y: 40 },
  { type: '热点区域', area: '直流母线电容', description: '局部温升约8°C，散热不均', temp: 62.1, x: 65, y: 30 },
  { type: '温度异常', area: '散热器入口', description: '风道局部堵塞，温差>10°C', temp: 58.7, x: 50, y: 70 },
]

const displayAnnotations = computed(() => (props.annotations?.length ? props.annotations : mockAnnotations))

const overlayMarks = computed(() => (activeTab.value === 'thermal' ? displayAnnotations.value : marks.value))

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) {
    imageFile.value = file
    imagePreview.value = URL.createObjectURL(file)
    ElMessage.success('图片已加载')
  } else { ElMessage.warning('请上传图片文件') }
}

function handleFileInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) {
    imageFile.value = file
    imagePreview.value = URL.createObjectURL(file)
  }
}

function removeAnnotation(idx: number) {
  const filtered = marks.value.filter((_, i) => i !== idx)
  marks.value = [...filtered]
}

function addMark(e: MouseEvent, target: HTMLElement) {
  const rect = target.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width * 100).toFixed(1)
  const y = ((e.clientY - rect.top) / rect.height * 100).toFixed(1)
  marks.value.push({ x: Number(x), y: Number(y), label: `标注 ${marks.value.length + 1}`, color: '#ff4d4f' })
}
</script>

<template>
  <div class="annotator tech-card">
    <div class="ann-header">
      <h4>🔬 多模态分析</h4>
      <div class="mode-tabs">
        <span class="m-tab" :class="{ active: activeTab === 'thermal' }" @click="activeTab = 'thermal'">🌡 红外</span>
        <span class="m-tab" :class="{ active: activeTab === 'visible' }" @click="activeTab = 'visible'">📷 可见光</span>
        <span class="m-tab" :class="{ active: activeTab === 'spectrum' }" @click="activeTab = 'spectrum'">📊 频谱</span>
      </div>
    </div>

    <div class="ann-body">
      <div class="image-panel" @dragover.prevent="isDragging = true" @dragleave="isDragging = false" @drop.prevent="handleDrop">
        <div v-if="imagePreview" class="image-wrapper" @click="(e: MouseEvent) => addMark(e, $el as HTMLElement)">
          <img :src="imagePreview" alt="分析图像" />
          <div v-for="(m, i) in overlayMarks" :key="i"
            class="mark-point" :style="{ left: ((m as any).x || 35 + i * 15) + '%', top: ((m as any).y || 30 + i * 20) + '%', background: (m as any).type?.includes?.('热点') ? '#ff4d4f' : '#ff9c40' }"
            :title="(m as any).description || (m as any).label">
            <span class="mark-temp" v-if="(m as any).temp">{{ (m as any).temp }}°C</span>
          </div>
        </div>
        <div v-else class="upload-zone" :class="{ dragging: isDragging }">
          <input type="file" accept="image/*" @change="handleFileInput" style="display:none" ref="fileInp" />
          <el-icon :size="40" color="rgba(0,240,255,0.25)"><component is="PictureFilled" /></el-icon>
          <p>拖拽红外热像图或设备照片到此处</p>
          <p class="hint">支持 JPG/PNG，自动分析温度异常区域</p>
          <el-button size="small" @click="($refs.fileInp as HTMLInputElement).click()">选择图片</el-button>
        </div>
      </div>

      <div class="annotation-list">
        <div class="al-title">分析结果 ({{ displayAnnotations.length }}项)</div>
        <div v-for="(a, i) in displayAnnotations" :key="i" class="al-item">
          <div class="ali-header">
            <span class="ali-dot" :style="{background: a.type?.includes('热点')?'#ff4d4f':'#ff9c40'}"></span>
            <el-tag size="small" :type="a.type?.includes('热点') ? 'danger' : 'warning'">{{ a.type }}</el-tag>
            <el-button size="small" text type="danger" @click="removeAnnotation(i)" v-if="!props.annotations?.length">✕</el-button>
          </div>
          <div class="ali-area">{{ a.area }}</div>
          <div class="ali-desc">{{ a.description }}</div>
          <div v-if="a.temp" class="ali-temp font-digital" :style="{color: (a.temp||0) > 80 ? '#ff4d4f' : (a.temp||0) > 60 ? '#ff9c40' : '#52c41a'}">{{ a.temp }}°C</div>
        </div>
        <div v-if="!displayAnnotations.length" class="empty-hint">暂无分析结果，上传图片后自动生成</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.annotator { display: flex; flex-direction: column; gap: 0; }
.ann-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.ann-header h4 { color: var(--color-accent); font-size: 14px; margin: 0; }
.mode-tabs { display: flex; gap: 4px; }
.m-tab { padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; color: var(--color-text-secondary); border: 1px solid transparent; transition: all 0.2s; }
.m-tab:hover { color: var(--color-accent); }
.m-tab.active { color: var(--color-accent); border-color: var(--color-accent); background: var(--color-accent-dim); }
.ann-body { display: flex; gap: 14px; }
.image-panel { flex: 1; min-height: 280px; }
.image-wrapper { position: relative; overflow: hidden; border-radius: 8px; border: 1px solid rgba(0,240,255,0.1); cursor: crosshair; }
.image-wrapper img { width: 100%; max-height: 350px; object-fit: contain; display: block; background: rgba(0,0,0,0.3); }
.mark-point { position: absolute; width: 14px; height: 14px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.6); transform: translate(-50%,-50%); cursor: pointer; z-index: 2; box-shadow: 0 0 8px rgba(255,77,79,0.5); animation: breathe 2s ease-in-out infinite; }
.mark-temp { position: absolute; top: -22px; left: 50%; transform: translateX(-50%); font-size: 10px; color: #fff; background: rgba(255,77,79,0.8); padding: 2px 6px; border-radius: 3px; white-space: nowrap; }
.upload-zone { height: 100%; min-height: 280px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; border: 2px dashed rgba(0,240,255,0.12); border-radius: 8px; transition: border-color 0.3s; cursor: pointer; }
.upload-zone:hover, .upload-zone.dragging { border-color: var(--color-accent); }
.upload-zone p { color: var(--color-text-secondary); font-size: 13px; }
.upload-zone .hint { font-size: 11px; opacity: 0.5; }
.annotation-list { width: 240px; max-height: 350px; overflow-y: auto; }
.al-title { font-size: 12px; color: var(--color-accent); margin-bottom: 10px; font-weight: 600; }
.al-item { padding: 10px; margin-bottom: 8px; background: rgba(0,240,255,0.03); border-radius: 6px; border: 1px solid rgba(0,240,255,0.06); }
.ali-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.ali-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ali-area { font-size: 13px; color: var(--color-text-primary); margin-bottom: 4px; }
.ali-desc { font-size: 11px; color: var(--color-text-secondary); line-height: 1.5; }
.ali-temp { font-size: 18px; font-weight: 700; margin-top: 4px; }
.empty-hint { text-align: center; color: var(--color-text-secondary); font-size: 12px; padding: 20px; }
</style>
