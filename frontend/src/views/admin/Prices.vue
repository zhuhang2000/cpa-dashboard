<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">模型定价</h1>
        <p class="page-desc">
          售价单位：{{ currency() }} / 百万 tokens。未单独定价的模型使用 CPA Manager Plus 同步的官方价 ×
          <b>{{ settings?.cpamp_price_multiplier ?? '—' }}</b> 倍率，可在<RouterLink to="/admin/settings"
            >系统设置</RouterLink
          >中调整。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" @click="openEdit(null)"><Icon name="plus" :size="16" />添加模型价格</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="input-group has-prefix search">
          <span class="input-prefix"><Icon name="search" :size="15" /></span>
          <input v-model.trim="q" class="input input-sm" placeholder="搜索模型" aria-label="搜索模型" />
        </div>
        <span class="muted">{{ filtered.length }} 个模型 · CPAMP 价格库 {{ cpampCount }} 条</span>
      </div>
      <EmptyState
        v-if="!loading && !filtered.length"
        icon="tag"
        title="暂无模型"
        desc="用户调用过的模型会自动出现在这里，也可以手动添加"
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>模型</th>
              <th>价格来源</th>
              <th class="right">售价 输入 / 输出</th>
              <th>前台显示</th>
              <th class="actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in filtered" :key="m.model">
              <td class="nowrap">
                <div class="mono cell-main">{{ m.model }}</div>
                <div class="cell-sub">
                  <template v-if="m.override?.note">{{ m.override.note }} · </template>
                  {{ m.calls ? `调用 ${num(m.calls)} 次 · ${relative(m.last_seen_ms)}` : '暂无调用' }}
                </div>
              </td>
              <td class="nowrap">
                <StatusBadge :map="PRICE_SOURCES" :value="m.source" />
                <div v-if="m.cpamp" class="cell-sub num" title="CPA Manager Plus 官方价（美元 / 百万 tokens）">
                  官方 {{ usd(m.cpamp.input) }} / {{ usd(m.cpamp.output) }}
                </div>
              </td>
              <td class="right num nowrap">
                <b>{{ m.price ? `${price(m.price.input)} / ${price(m.price.output)}` : '—' }}</b>
                <div v-if="m.price" class="cell-sub">
                  缓存 {{ price(m.price.cache_read) }} / {{ price(m.price.cache_write) }}
                </div>
              </td>
              <td>
                <label class="toggle">
                  <input type="checkbox" :checked="!m.hidden" @change="setHidden(m, !$event.target.checked)" />
                  <span class="toggle-track" />
                </label>
              </td>
              <td class="actions">
                <button class="link-btn" @click="openEdit(m)">{{ m.override ? '编辑' : '设置价格' }}</button>
                <button v-if="m.override" class="link-btn danger" @click="removeOverride(m)">恢复默认</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Modal
      :open="formOpen"
      :title="editingModel ? `设置价格：${editingModel}` : '添加模型价格'"
      @close="formOpen = false"
    >
      <form id="price-form" @submit.prevent="save">
        <div v-if="!editingModel" class="field">
          <label for="p-model">模型名称</label>
          <input
            id="p-model"
            v-model.trim="form.model"
            class="input mono"
            placeholder="与请求中的 model 完全一致，如 gpt-5"
            required
          />
        </div>
        <div class="grid grid-2" style="gap: 12px">
          <div class="field">
            <label for="p-in">输入价格</label>
            <input id="p-in" v-model="form.input" class="input" type="number" min="0" step="any" required />
          </div>
          <div class="field">
            <label for="p-out">输出价格</label>
            <input id="p-out" v-model="form.output" class="input" type="number" min="0" step="any" required />
          </div>
          <div class="field">
            <label for="p-cr">缓存读取价格 <span class="faint">（选填）</span></label>
            <input
              id="p-cr"
              v-model="form.cache_read"
              class="input"
              type="number"
              min="0"
              step="any"
              :placeholder="`默认 输入×0.1`"
            />
          </div>
          <div class="field">
            <label for="p-cw">缓存写入价格 <span class="faint">（选填）</span></label>
            <input
              id="p-cw"
              v-model="form.cache_write"
              class="input"
              type="number"
              min="0"
              step="any"
              :placeholder="`默认 输入×1.25`"
            />
          </div>
        </div>
        <div class="field">
          <label for="p-note">说明 <span class="faint">（选填，前台可见）</span></label>
          <input
            id="p-note"
            v-model.trim="form.note"
            class="input"
            maxlength="100"
            placeholder="例如：支持 1M 上下文"
          />
        </div>
        <div v-if="editingRow?.cpamp" class="alert alert-info">
          <Icon name="info" :size="16" />
          <div class="alert-body">
            CPAMP 官方价（美元 / 百万 tokens）：输入 {{ usd(editingRow.cpamp.input) }}，输出
            {{ usd(editingRow.cpamp.output) }}， 缓存读 {{ usd(editingRow.cpamp.cache_read) }}，缓存写
            {{ usd(editingRow.cpamp.cache_write) }}
            <button type="button" class="link-btn" style="margin-left: 6px" @click="fillReference">
              按倍率 ×{{ multiplier }} 填入
            </button>
          </div>
        </div>
      </form>
      <template #footer>
        <button class="btn" @click="formOpen = false">取消</button>
        <button class="btn btn-primary" form="price-form" :disabled="saving">保存</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import Modal from '@/components/Modal.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api'
import { PRICE_SOURCES } from '@/constants'
import { currency, num, price, relative } from '@/utils/format'
import { toast } from '@/toast'

const items = ref([])
const cpampCount = ref(0)
const settings = ref(null)
const loading = ref(false)
const saving = ref(false)
const q = ref('')
const formOpen = ref(false)
const editingModel = ref('')
const form = reactive({ model: '', input: '', output: '', cache_read: '', cache_write: '', note: '' })

const filtered = computed(() => {
  const term = q.value.toLowerCase()
  return term ? items.value.filter((m) => m.model.toLowerCase().includes(term)) : items.value
})
const editingRow = computed(() => items.value.find((m) => m.model === editingModel.value))

async function load() {
  loading.value = true
  try {
    const [prices, conf] = await Promise.all([api.get('/api/admin/prices'), api.get('/api/admin/settings')])
    items.value = prices.items
    cpampCount.value = prices.cpamp_models
    settings.value = conf.settings
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function openEdit(m) {
  editingModel.value = m ? m.model : ''
  const o = m?.override
  const p = m?.price
  Object.assign(form, {
    model: m ? m.model : '',
    input: o ? o.input : p ? p.input : '',
    output: o ? o.output : p ? p.output : '',
    cache_read: o?.cache_read ?? '',
    cache_write: o?.cache_write ?? '',
    note: o?.note || '',
  })
  formOpen.value = true
}

const multiplier = computed(() => Number(settings.value?.cpamp_price_multiplier) || 1)

function usd(v) {
  if (v === null || v === undefined) return '—'
  return `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })}`
}

// The form holds selling prices, so the USD reference is converted with the multiplier.
function fillReference() {
  const ref = editingRow.value?.cpamp
  if (!ref) return
  const k = multiplier.value
  const conv = (v) => Number((v * k).toFixed(6))
  Object.assign(form, {
    input: conv(ref.input),
    output: conv(ref.output),
    cache_read: conv(ref.cache_read),
    cache_write: conv(ref.cache_write),
  })
}

async function save() {
  saving.value = true
  try {
    await api.put('/api/admin/prices', {
      model: editingModel.value || form.model,
      input: form.input,
      output: form.output,
      cache_read: form.cache_read === '' ? null : form.cache_read,
      cache_write: form.cache_write === '' ? null : form.cache_write,
      note: form.note,
    })
    toast.success('价格已保存，新的调用将按此价格计费')
    formOpen.value = false
    await load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

async function removeOverride(m) {
  try {
    await api.post('/api/admin/prices/delete', { model: m.model })
    toast.success('已恢复默认定价')
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function setHidden(m, hidden) {
  try {
    await api.post('/api/admin/prices/visibility', { model: m.model, hidden })
    m.hidden = hidden
    toast.success(hidden ? '已在前台价格页隐藏' : '已在前台价格页显示')
  } catch (e) {
    toast.error(e.message)
  }
}

onMounted(load)
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
