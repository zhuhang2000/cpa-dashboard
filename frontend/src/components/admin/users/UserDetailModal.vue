<template>
  <Modal open xwide :title="title" :persistent="deleting" @close="close">
    <template #header>
      <div class="detail-head">
        <div class="modal-title">{{ title }}</div>
        <div v-if="!removing" class="tabs">
          <button
            v-for="t in tabs"
            :key="t.key"
            type="button"
            class="tab"
            :class="{ active: tab === t.key }"
            @click="setTab(t.key)"
          >
            {{ t.label }}
          </button>
        </div>
      </div>
    </template>
    <div v-if="removing" class="stack">
      <p>
        确定删除用户 <b>{{ user.username }}</b> 的密钥 <b>{{ removing.name }}</b> 吗？
      </p>
      <code class="key-value">{{ removing.key }}</code>
      <p class="muted">删除后无法恢复。同步完成后失效，历史记录保留。</p>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
    </div>
    <div v-else-if="tab === 'keys'" class="stack">
      <div class="row detail-toolbar">
        <span class="muted">{{ items.length }} 个密钥 · 可复制到 CPA 中查找</span>
        <button type="button" class="btn btn-sm" :disabled="loading" @click="loadKeys">
          <Icon name="refresh" :size="15" />刷新
        </button>
      </div>
      <div v-if="user.status === UserStatus.BANNED" class="alert alert-warning">
        <Icon name="lock" :size="16" />
        <div class="alert-body">该账号已禁用，所有密钥均无法调用。</div>
      </div>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <div v-if="loading && !items.length" class="stack" aria-label="正在加载密钥">
        <div v-for="i in 3" :key="i" class="skeleton" style="height: 100px" />
      </div>
      <EmptyState v-else-if="!items.length && !error" icon="key" title="该用户没有 API 密钥" />
      <article v-for="item in items" :key="item.id" class="card card-body key-card">
        <div class="row key-heading">
          <span class="cell-main key-name">{{ item.name }}</span>
          <StatusBadge :map="keyStates" :value="item.state" />
          <button type="button" class="link-btn danger" :disabled="loading" @click="confirmDelete(item)">删除</button>
        </div>
        <div class="row key-content">
          <code class="key-value">{{ item.key }}</code>
          <CopyButton :text="item.key" label="复制" />
        </div>
        <div class="muted key-details">
          <span>{{ num(item.request_count) }} 次调用</span>
          <span :title="dateTime(item.last_used_at)">
            {{ item.last_used_at ? `最近使用：${relative(item.last_used_at)}` : '从未使用' }}
          </span>
          <span :title="dateTime(item.created_at)">创建于 {{ date(item.created_at) }}</span>
        </div>
      </article>
    </div>
    <div v-else-if="tab === 'ledger'" class="stack">
      <div class="row detail-toolbar">
        <span class="muted">{{ num(ledger.total) }} 条记录 · 调用扣费不计入流水，请在「调用记录」中查看</span>
        <button type="button" class="btn btn-sm" :disabled="ledger.loading" @click="ledger.load()">
          <Icon name="refresh" :size="15" />刷新
        </button>
      </div>
      <div class="card">
        <TransactionTable :list="ledger" />
      </div>
    </div>
    <div v-else class="stack">
      <div class="row detail-toolbar">
        <span class="muted">{{ num(calls.total) }} 次调用 · 共消费 {{ money(calls.sum_cost) }}</span>
        <button type="button" class="btn btn-sm" :disabled="calls.loading" @click="calls.load()">
          <Icon name="refresh" :size="15" />刷新
        </button>
      </div>
      <div class="card">
        <div v-if="calls.loading && !calls.items.length" class="card-body stack" style="gap: 10px">
          <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
        </div>
        <EmptyState v-else-if="!calls.items.length" icon="activity" title="暂无调用记录" />
        <UsageLogTable v-else :items="calls.items" />
        <div v-if="calls.total" class="card-footer">
          <Pagination :page="calls.page" :total="calls.total" :page-size="calls.page_size" @change="calls.load" />
        </div>
      </div>
    </div>
    <template #footer>
      <template v-if="removing">
        <button type="button" class="btn" :disabled="deleting" @click="cancelDelete">返回列表</button>
        <button type="button" class="btn btn-danger" :disabled="deleting" @click="remove">
          {{ deleting ? '删除中…' : '确认删除' }}
        </button>
      </template>
      <button v-else type="button" class="btn" @click="close">关闭</button>
    </template>
  </Modal>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import CopyButton from '@/components/base/CopyButton.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Modal from '@/components/base/Modal.vue'
import Pagination from '@/components/base/Pagination.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import TransactionTable from '@/components/shared/TransactionTable.vue'
import UsageLogTable from '@/components/shared/UsageLogTable.vue'
import { keysApi } from '@/api/api_keys'
import { billingApi } from '@/api/billing'
import { usageApi } from '@/api/usage'
import { usePagedList } from '@/composables/usePagedList'
import { KEY_STATES, KeyState, Role, UserStatus } from '@/constants'
import { store } from '@/store'
import { date, dateTime, money, num, relative } from '@/utils/format'
import { toast } from '@/toast'

const TABS = [
  { key: 'keys', label: 'API 密钥' },
  { key: 'ledger', label: '余额流水' },
  { key: 'usage', label: '调用记录' },
]

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close', 'deleted'])
// A key would let a tag manager spend the user's balance, so only the system administrator sees keys.
const tabs = store.user?.role === Role.ADMIN ? TABS : TABS.filter((t) => t.key !== 'keys')
const tab = ref(tabs[0].key)
const items = ref([])
const loading = ref(false)
const deleting = ref(false)
const removing = ref(null)
const error = ref('')
let mounted = true

// Each tab loads the first time it is opened.
const ledger = usePagedList((query) => billingApi.adminListTransactions(props.user.id, query))
const calls = usePagedList(
  (query) => usageApi.adminUsageLogs(props.user.id, query),
  () => ({}),
  { sum_cost: 0 },
)
const lists = { ledger, usage: calls }
const opened = new Set()

const title = computed(() => (removing.value ? '删除 API 密钥' : `用户详情 · ${props.user.username}`))

const keyStates = computed(() =>
  props.user.status === UserStatus.BANNED
    ? { ...KEY_STATES, [KeyState.SUSPENDED]: { label: '账号已禁用', tone: 'danger' } }
    : KEY_STATES,
)

function setTab(key) {
  tab.value = key
  if (opened.has(key)) return
  opened.add(key)
  if (key === 'keys') loadKeys()
  else lists[key].load(1)
}

async function loadKeys() {
  if (loading.value || deleting.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await keysApi.adminListKeys(props.user.id)
    if (mounted) items.value = data.items
  } catch (e) {
    if (mounted) error.value = e.message
  } finally {
    if (mounted) loading.value = false
  }
}

function confirmDelete(item) {
  if (loading.value || deleting.value) return
  error.value = ''
  removing.value = item
}

function cancelDelete() {
  if (deleting.value) return
  removing.value = null
  error.value = ''
}

async function remove() {
  if (!removing.value || deleting.value) return
  deleting.value = true
  error.value = ''
  const keyId = removing.value.id
  try {
    await keysApi.adminDeleteKey(props.user.id, keyId)
    if (!mounted) return
    items.value = items.value.filter((item) => item.id !== keyId)
    removing.value = null
    emit('deleted')
    toast.success('已删除密钥，同步完成后失效，历史记录保留')
  } catch (e) {
    if (mounted) error.value = e.message
  } finally {
    if (mounted) deleting.value = false
  }
}

function close() {
  if (!deleting.value) emit('close')
}

onMounted(() => setTab(tab.value))
onBeforeUnmount(() => {
  mounted = false
  items.value = []
  removing.value = null
})
</script>

<style scoped>
.detail-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 16px;
  min-width: 0;
}
.detail-toolbar {
  justify-content: space-between;
  flex-wrap: wrap;
}
.key-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.key-heading {
  gap: 10px;
}
.key-name {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.key-content {
  align-items: flex-start;
  gap: 8px;
}
.key-content .key-value {
  flex: 1;
  min-width: 0;
}
.key-content :deep(button) {
  flex: none;
}
.key-value {
  white-space: normal;
  overflow-wrap: anywhere;
  user-select: all;
}
.key-details {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 12px;
}
</style>
