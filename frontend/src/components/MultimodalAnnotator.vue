<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  imageUrl?: string;
  annotations?: Array<{ type: string; area: string; description: string; temp?: number }>;
  mode?: 'thermal' | 'visible' | 'spectrum';
}>()

const activeTab = ref('image')
const mockAnnotations = [
  { type: '热点区域', area: 'IGBT模块A相', description: '温度异常，比周围高15°C', temp: 85.3 },
  { type: '热点区域', area: '直流母线电容', description: '局部温升约8°C', temp: 62.1 },
]
</script>

<template>
  <div class="annotator tech-card">
    <h4>🔬 多模态分析</h4>
    <div class="tabs">
      <span class="tab" :class="{ active: activeTab === 'image' }" @click="activeTab = 'image'">📷 图像</span>
      <span class="tab" :class="{ active: activeTab === 'thermal' }" @click="activeTab = 'thermal'">🌡 红外</span>
      <span class="tab" :class="{ active: activeTab === 'spectrum' }" @click="activeTab = 'spectrum'">📊 频谱</span>
    </div>

    <div class="annotator-content">
      <div class="image-area">
        <div v-if="imageUrl" class="image-preview">
          <img :src="imageUrl" alt="分析图像" />
        </div>
        <div v-else class="upload-zone">
          <el-icon :size="32" color="#8892a4"><component is="UploadFilled" /></el-icon>
          <p>拖拽或点击上传图片</p>
          <el-button size="small" type="primary" disabled>上传分析</el-button>
        </div>
      </div>

      <div class="annotations-list">
        <div class="ann-title">分析结果</div>
        <div v-for="(a, i) in (annotations?.length ? annotations : mockAnnotations)" :key="i" class="ann-item">
          <div class="ann-header">
            <el-tag size="small" :type="a.type.includes('热点') ? 'danger' : 'warning'">{{ a.type }}</el-tag>
            <span class="ann-area">{{ a.area }}</span>
          </div>
          <div class="ann-desc">{{ a.description }}</div>
          <div v-if="a.temp" class="ann-temp font-digital">{{ a.temp }}°C</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.annotator { h4 { color: var(--color-accent); margin-bottom: 10px; font-size: 13px; } }
.tabs { display: flex; gap: 4px; margin-bottom: 12px; }
.tab { padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; color: var(--color-text-secondary); border: 1px solid transparent; }
.tab.active { color: var(--color-accent); border-color: var(--color-accent); background: var(--color-accent-dim); }
.annotator-content { display: flex; gap: 12px; }
.image-area { flex: 1; min-height: 200px; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2); border-radius: 6px; border: 1px dashed rgba(0,240,255,0.15); }
.image-preview img { max-width: 100%; max-height: 250px; object-fit: contain; }
.upload-zone { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--color-text-secondary); font-size: 12px; }
.upload-zone p { margin: 4px 0; }
.annotations-list { width: 220px; }
.ann-title { font-size: 12px; color: var(--color-accent); margin-bottom: 8px; font-weight: 600; }
.ann-item { padding: 8px; margin-bottom: 6px; background: rgba(0,240,255,0.04); border-radius: 4px; }
.ann-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.ann-area { font-size: 12px; }
.ann-desc { font-size: 11px; color: var(--color-text-secondary); }
.ann-temp { font-size: 16px; color: #ff4d4f; margin-top: 4px; }
</style>
