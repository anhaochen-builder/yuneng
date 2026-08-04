<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { knowledgeApi } from '@/api'

const query = ref('')
const results = ref<any[]>([])
const searching = ref(false)

async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try {
    const r = await knowledgeApi.search(query.value, 5)
    results.value = (r.data || r).results || (r.data || r).result || []
  } catch { ElMessage.error('检索失败') }
  searching.value = false
}
</script>

<template>
  <div class="knowledge-page animate-fade-in">
    <div class="search-bar tech-card">
      <el-input v-model="query" placeholder="搜索知识库，如：IGBT过热原因" size="large" @keyup.enter="search">
        <template #append><el-button @click="search" :loading="searching" icon="Search">搜索</el-button></template>
      </el-input>
    </div>

    <div class="results" v-if="results.length">
      <div v-for="(r, i) in results" :key="i" class="result-item tech-card">
        <div class="result-idx">#{{ i + 1 }}</div>
        <div class="result-text">{{ r.text || r.content || JSON.stringify(r) }}</div>
        <div v-if="r.score" class="result-score">相关度: {{ (r.score * 100).toFixed(0) }}%</div>
      </div>
    </div>
    <div v-else class="tech-card empty-state">
      <p>输入关键词搜索知识库，当前共 158 条知识文档</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.knowledge-page { display: flex; flex-direction: column; gap: 16px; }
.search-bar { padding: 16px 24px; }
.results { display: flex; flex-direction: column; gap: 10px; }
.result-item { display: flex; gap: 12px; align-items: flex-start; padding: 14px 18px; }
.result-idx { color: var(--color-accent); font-weight: 700; font-size: 14px; }
.result-text { flex: 1; font-size: 13px; line-height: 1.7; color: var(--color-text-primary); }
.result-score { font-size: 12px; color: var(--color-text-secondary); white-space: nowrap; }
.empty-state { text-align: center; color: var(--color-text-secondary); padding: 40px; }
</style>
