<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">模型价格</h1>
        <p class="page-desc">按实际消耗的 tokens 计费，失败的请求不收费。</p>
      </div>
      <div class="page-actions">
        <div class="tabs">
          <button class="tab" :class="{ active: unit === 'M' }" @click="unit = 'M'">每百万 tokens</button>
          <button class="tab" :class="{ active: unit === 'K' }" @click="unit = 'K'">每千 tokens</button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="input-group has-prefix search">
          <span class="input-prefix"><Icon name="search" :size="15" /></span>
          <input v-model.trim="q" class="input input-sm" placeholder="搜索模型" aria-label="搜索模型" />
        </div>
        <span class="muted">{{ filtered.length }} 个模型</span>
      </div>
      <div v-if="loading" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState v-else-if="!filtered.length" icon="tag" :title="q ? '没有匹配的模型' : '暂无模型价格'" :desc="q ? '' : '管理员配置价格后会显示在这里'" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>模型</th>
              <th class="right">输入</th>
              <th class="right">输出</th>
              <th class="right">缓存读取</th>
              <th class="right">缓存写入</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in filtered" :key="m.model">
              <td>
                <div class="row" style="gap: 4px">
                  <span class="mono cell-main">{{ m.model }}</span>
                  <CopyButton :text="m.model" />
                </div>
              </td>
              <td class="right num">{{ show(m.input) }}</td>
              <td class="right num">{{ show(m.output) }}</td>
              <td class="right num muted">{{ show(m.cache_read) }}</td>
              <td class="right num muted">{{ show(m.cache_write) }}</td>
              <td class="muted">{{ m.note }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-footer muted" style="font-size: 12.5px">
        <span>费用 = 输入 tokens × 输入单价 + 输出 tokens × 输出单价（命中缓存的输入按缓存价格计算），推理 tokens 计入输出。</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import CopyButton from '../components/CopyButton.vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import { api } from '../api'
import { price } from '../format'
import { toast } from '../toast'

const items = ref([])
const loading = ref(true)
const q = ref('')
const unit = ref('M')

const filtered = computed(() => {
  const term = q.value.toLowerCase()
  return term ? items.value.filter((m) => m.model.toLowerCase().includes(term)) : items.value
})

function show(v) {
  if (v === null || v === undefined) return '—'
  return price(unit.value === 'K' ? v / 1000 : v)
}

onMounted(async () => {
  try {
    items.value = (await api.get('/api/pricing')).items
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.search {
  width: 260px;
  max-width: 100%;
}
.search .input {
  padding-left: 32px;
}
</style>
