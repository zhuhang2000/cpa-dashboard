<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">用量明细</h1>
        <p class="page-desc">每一次调用的模型、tokens 与费用。数据通常在请求完成后 15 秒内出现。</p>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="loading" @click="load"><Icon name="refresh" :size="16" />刷新</button>
        <a class="btn" :href="exportHref" download><Icon name="download" :size="16" />导出 CSV</a>
      </div>
    </div>

    <div class="card">
      <div class="card-body filters">
        <div class="tabs">
          <button v-for="p in presets" :key="p.key" class="tab" :class="{ active: range === p.key }" @click="setRange(p.key)">{{ p.label }}</button>
        </div>
        <template v-if="range === 'custom'">
          <input v-model="customStart" class="input input-sm" type="date" aria-label="开始日期" @change="apply" />
          <span class="muted">至</span>
          <input v-model="customEnd" class="input input-sm" type="date" aria-label="结束日期" @change="apply" />
        </template>
        <select v-model="keyId" class="select input-sm" aria-label="密钥" @change="apply">
          <option value="">全部密钥</option>
          <option v-for="k in keys" :key="k.id" :value="String(k.id)">{{ k.name }}</option>
        </select>
        <select v-model="model" class="select input-sm" aria-label="模型" @change="apply">
          <option value="">全部模型</option>
          <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
        </select>
        <select v-model="status" class="select input-sm" aria-label="状态" @change="apply">
          <option value="">全部状态</option>
          <option value="success">成功</option>
          <option value="failed">失败</option>
        </select>
      </div>
      <div class="summary-bar">
        <span>请求 <b class="num">{{ num(data.total) }}</b> 次</span>
        <span>消费 <b class="num">{{ money(data.sum_cost) }}</b></span>
        <span>Tokens <b class="num">{{ tokens(data.sum_tokens) }}</b></span>
      </div>
      <div v-if="loading && !data.items.length" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState v-else-if="!data.items.length" icon="activity" title="没有符合条件的调用记录" desc="调整筛选条件，或使用 API 密钥发起一次调用" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>时间</th>
              <th>密钥</th>
              <th>模型</th>
              <th class="right">输入</th>
              <th class="right">输出</th>
              <th class="right">费用</th>
              <th>状态 / 耗时</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in data.items" :key="r.id">
              <td class="nowrap num" :title="dateTime(r.ts, { seconds: true })">{{ shortTime(r.ts) }}</td>
              <td class="nowrap">{{ r.key_name }}</td>
              <td>
                <div class="mono nowrap">{{ r.model }}</div>
                <div v-if="r.endpoint" class="cell-sub mono">{{ r.endpoint }}</div>
              </td>
              <td class="right num nowrap" :title="inputTitle(r)">
                {{ tokens(r.input_tokens + r.cache_read_tokens + r.cache_write_tokens) }}
                <div v-if="r.cache_read_tokens || r.cache_write_tokens" class="cell-sub">
                  缓存 {{ tokens(r.cache_read_tokens + r.cache_write_tokens) }}
                </div>
              </td>
              <td class="right num nowrap" :title="r.reasoning_tokens ? `其中推理 ${num(r.reasoning_tokens)}` : ''">
                {{ tokens(r.output_tokens) }}
                <div v-if="r.reasoning_tokens" class="cell-sub">推理 {{ tokens(r.reasoning_tokens) }}</div>
              </td>
              <td class="right num nowrap"><b>{{ money(r.cost) }}</b></td>
              <td class="nowrap">
                <span class="badge" :class="r.failed ? 'badge-danger' : 'badge-success'">{{ r.failed ? '失败' : '成功' }}</span>
                <div class="cell-sub num">
                  {{ duration(r.latency_ms) }}<template v-if="r.stream !== null"> · {{ r.stream ? '流式' : '非流式' }}</template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="data.total" class="card-footer">
        <Pagination :page="page" :total="data.total" :page-size="pageSize" @change="go" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import Pagination from '../components/Pagination.vue'
import { api, exportUrl } from '../api'
import { dateTime, duration, fromInputDate, money, num, toInputDate, tokens } from '../format'
import { toast } from '../toast'

const presets = [
  { key: 'today', label: '今天' },
  { key: '7d', label: '近 7 天' },
  { key: '30d', label: '近 30 天' },
  { key: 'all', label: '全部' },
  { key: 'custom', label: '自定义' },
]
const range = ref('7d')
const customStart = ref(toInputDate(Date.now() - 6 * 86400000))
const customEnd = ref(toInputDate(Date.now()))
const keyId = ref('')
const model = ref('')
const status = ref('')
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const keys = ref([])
const models = ref([])
const data = reactive({ items: [], total: 0, sum_cost: 0, sum_tokens: 0 })

function startOfToday() {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

const filters = computed(() => {
  let start = null
  let end = null
  if (range.value === 'today') start = startOfToday()
  else if (range.value === '7d') start = startOfToday() - 6 * 86400000
  else if (range.value === '30d') start = startOfToday() - 29 * 86400000
  else if (range.value === 'custom') {
    start = fromInputDate(customStart.value)
    end = fromInputDate(customEnd.value, true)
  }
  return { start, end, key_id: keyId.value, model: model.value, status: status.value }
})

const exportHref = computed(() => exportUrl('/api/usage/export', filters.value))

function shortTime(ms) {
  const full = dateTime(ms, { seconds: true })
  return new Date(ms).getFullYear() === new Date().getFullYear() ? full.slice(5) : full
}

function inputTitle(r) {
  return `未缓存 ${num(r.input_tokens)} · 缓存读取 ${num(r.cache_read_tokens)} · 缓存写入 ${num(r.cache_write_tokens)}`
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/api/usage/logs', { ...filters.value, page: page.value, page_size: pageSize })
    Object.assign(data, res)
    models.value = res.models
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function apply() {
  page.value = 1
  load()
}
function setRange(key) {
  range.value = key
  apply()
}
function go(p) {
  page.value = p
  load()
}

onMounted(async () => {
  load()
  try {
    keys.value = (await api.get('/api/keys')).items
  } catch {
    /* filter list is optional */
  }
})
</script>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding-bottom: 14px;
}
.filters .input,
.filters .select {
  width: auto;
  min-width: 140px;
}
.summary-bar {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  padding: 10px 20px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--muted);
  font-size: 13px;
}
.summary-bar b {
  color: var(--text);
  margin: 0 2px;
}
</style>
