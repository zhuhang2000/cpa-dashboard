<template>
  <Modal
    open
    wide
    :title="removing ? '删除 API 密钥' : `${user.username} 的 API 密钥`"
    :persistent="deleting"
    @close="close"
  >
    <div v-if="removing" class="stack">
      <p>
        确定删除用户 <b>{{ user.username }}</b> 的密钥 <b>{{ removing.name }}</b> 吗？
      </p>
      <code class="key-value">{{ removing.key }}</code>
      <p class="muted">删除后无法恢复。同步完成后失效，历史记录保留。</p>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
    </div>
    <div v-else class="stack">
      <div class="row key-toolbar">
        <span class="muted">{{ items.length }} 个密钥 · 可复制到 CPA 中查找</span>
        <button type="button" class="btn btn-sm" :disabled="loading" @click="load">
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
import CopyButton from '@/components/CopyButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import Modal from '@/components/Modal.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { keysApi } from '@/api/api_keys'
import { KEY_STATES, KeyState, UserStatus } from '@/constants'
import { date, dateTime, num, relative } from '@/utils/format'
import { toast } from '@/toast'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close', 'deleted'])
const items = ref([])
const loading = ref(false)
const deleting = ref(false)
const removing = ref(null)
const error = ref('')
let mounted = true

const keyStates = computed(() =>
  props.user.status === UserStatus.BANNED
    ? { ...KEY_STATES, [KeyState.SUSPENDED]: { label: '账号已禁用', tone: 'danger' } }
    : KEY_STATES,
)

async function load() {
  if (loading.value || deleting.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await keysApi.listUserKeys(props.user.id)
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
    await keysApi.deleteUserKey(props.user.id, keyId)
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

onMounted(load)
onBeforeUnmount(() => {
  mounted = false
  items.value = []
  removing.value = null
})
</script>

<style scoped>
.key-toolbar {
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
