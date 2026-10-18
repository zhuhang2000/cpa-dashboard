<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">API 密钥</h1>
        <p class="page-desc">密钥用于调用接口，请妥善保管。可为每个密钥设置额度上限与过期时间。</p>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="loading" @click="load"><Icon name="refresh" :size="16" />刷新</button>
        <button class="btn btn-primary" :disabled="atLimit" @click="openCreate">
          <Icon name="plus" :size="16" />创建密钥
        </button>
      </div>
    </div>

    <div v-if="(store.user?.balance ?? 1) <= 0" class="alert alert-warning">
      <Icon name="alert" :size="16" />
      <div class="alert-body">
        账户余额不足，所有密钥已暂停调用。<RouterLink to="/recharge">立即充值</RouterLink> 后会在几秒内自动恢复。
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">我的密钥</div>
        <span class="muted">{{ items.length }} / {{ maxKeys }}</span>
      </div>
      <div v-if="loading && !items.length" class="card-body stack" style="gap: 12px">
        <div v-for="i in 3" :key="i" class="skeleton" style="height: 40px" />
      </div>
      <EmptyState
        v-else-if="!items.length"
        icon="key"
        title="还没有 API 密钥"
        desc="创建一个密钥，即可开始调用模型接口"
      >
        <button class="btn btn-primary" @click="openCreate"><Icon name="plus" :size="16" />创建密钥</button>
      </EmptyState>
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>名称</th>
              <th>密钥</th>
              <th>状态</th>
              <th>已用 / 额度</th>
              <th>最近使用</th>
              <th class="actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="k in items" :key="k.id">
              <td class="nowrap">
                <div class="cell-main">{{ k.name }}</div>
                <div class="cell-sub">创建于 {{ date(k.created_at) }}</div>
              </td>
              <td>
                <div class="row" style="gap: 4px">
                  <code class="nowrap">{{ k.masked }}</code>
                  <CopyButton :text="() => reveal(k)" />
                </div>
              </td>
              <td>
                <StatusBadge :map="KEY_STATES" :value="k.state" />
              </td>
              <td class="nowrap" style="min-width: 140px">
                <div class="num">
                  {{ money(k.used) }}
                  <span class="muted"> / {{ k.quota === null ? '不限' : money(k.quota) }}</span>
                </div>
                <div v-if="k.quota" class="progress" :class="quotaClass(k)" style="margin: 6px 0 2px">
                  <div :style="{ width: `${Math.min(100, (k.used / k.quota) * 100)}%` }" />
                </div>
                <div class="cell-sub num">{{ num(k.request_count) }} 次调用</div>
              </td>
              <td class="nowrap">
                <div :title="dateTime(k.last_used_at)">{{ relative(k.last_used_at) }}</div>
                <div class="cell-sub">{{ k.expires_at ? `${date(k.expires_at - 1)} 到期` : '永不过期' }}</div>
              </td>
              <td class="actions">
                <button class="link-btn" @click="openEdit(k)">编辑</button>
                <button class="link-btn" @click="toggle(k)">
                  {{ k.status === KeyStatus.ACTIVE ? '禁用' : '启用' }}
                </button>
                <button class="link-btn danger" @click="removing = k">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card card-body">
      <div class="row" style="gap: 10px; align-items: flex-start">
        <Icon name="info" :size="16" class="muted" style="margin-top: 2px; flex: none" />
        <div class="muted" style="font-size: 13px">
          状态说明：<b>余额不足</b> 时所有密钥会被暂停，充值后自动恢复；<b>额度用尽</b>
          表示该密钥已达到你设置的额度上限，可在编辑中调高；禁用、删除的密钥会在数秒内失效。
        </div>
      </div>
    </div>

    <!-- create / edit -->
    <Modal :open="formOpen" :title="editing ? '编辑密钥' : '创建密钥'" @close="formOpen = false">
      <form id="key-form" @submit.prevent="save">
        <div class="field">
          <label for="key-name">名称</label>
          <input
            id="key-name"
            v-model.trim="form.name"
            class="input"
            maxlength="32"
            placeholder="例如：生产环境、我的笔记本"
          />
        </div>
        <div class="field">
          <label for="key-quota">额度上限 <span class="faint">（选填）</span></label>
          <div class="input-group has-prefix">
            <span class="input-prefix">{{ currency() }}</span>
            <input
              id="key-quota"
              v-model="form.quota"
              class="input"
              type="number"
              min="0"
              step="0.01"
              placeholder="不填表示不限额"
            />
          </div>
          <div class="field-hint">
            该密钥累计消费达到上限后自动停用{{ editing ? `，当前已用 ${money(editing.used)}` : '' }}
          </div>
        </div>
        <div class="field">
          <label for="key-exp">过期日期 <span class="faint">（选填）</span></label>
          <input id="key-exp" v-model="form.expires" class="input" type="date" :min="tomorrow" />
          <div class="field-hint">到期当天结束后失效，不填表示永不过期</div>
        </div>
      </form>
      <template #footer>
        <button class="btn" @click="formOpen = false">取消</button>
        <button class="btn btn-primary" form="key-form" :disabled="saving">
          {{ saving ? '保存中…' : editing ? '保存' : '创建' }}
        </button>
      </template>
    </Modal>

    <!-- show the new key once -->
    <Modal :open="!!createdKey" title="密钥已创建" persistent @close="createdKey = ''">
      <div class="alert alert-warning" style="margin-bottom: 14px">
        <Icon name="alert" :size="16" />
        <div class="alert-body">请立即复制并妥善保存。密钥等同于你的账户余额，切勿泄露或提交到公开仓库。</div>
      </div>
      <div class="key-box">
        <span>{{ createdKey }}</span>
        <CopyButton :text="createdKey" variant="default" size="md" label="复制" />
      </div>
      <template #footer>
        <button class="btn btn-primary" @click="createdKey = ''">我已保存</button>
      </template>
    </Modal>

    <Modal :open="!!removing" title="删除密钥" @close="removing = null">
      <p>
        确定删除密钥 <b>{{ removing?.name }}</b
        >（<code>{{ removing?.masked }}</code
        >）吗？删除后使用该密钥的请求会立即失败，且无法恢复。
      </p>
      <template #footer>
        <button class="btn" @click="removing = null">取消</button>
        <button class="btn btn-danger" :disabled="saving" @click="remove">删除</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CopyButton from '@/components/CopyButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import Modal from '@/components/Modal.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api'
import { KEY_STATES, KeyStatus } from '@/constants'
import { refreshUser, store } from '@/store'
import { currency, date, dateTime, fromInputDate, money, num, relative, toInputDate } from '@/utils/format'
import { toast } from '@/toast'

const route = useRoute()
const router = useRouter()
const items = ref([])
const maxKeys = ref(store.status?.max_keys_per_user || 10)
const loading = ref(false)
const saving = ref(false)
const formOpen = ref(false)
const editing = ref(null)
const removing = ref(null)
const createdKey = ref('')
const form = reactive({ name: '', quota: '', expires: '' })

const atLimit = computed(() => items.value.length >= maxKeys.value)
const tomorrow = computed(() => toInputDate(Date.now() + 86400000))

function quotaClass(k) {
  const ratio = k.used / k.quota
  return ratio >= 1 ? 'full' : ratio >= 0.8 ? 'warn' : ''
}

async function load() {
  loading.value = true
  try {
    const data = await api.get('/api/keys')
    items.value = data.items
    maxKeys.value = data.max_keys
    store.keyCount = data.items.length
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

async function reveal(k) {
  try {
    const data = await api.post(`/api/keys/${k.id}/reveal`)
    return data.key
  } catch (e) {
    toast.error(e.message)
    return ''
  }
}

function openCreate() {
  if (atLimit.value) {
    toast.error(`最多只能创建 ${maxKeys.value} 个密钥`)
    return
  }
  editing.value = null
  Object.assign(form, { name: '', quota: '', expires: '' })
  formOpen.value = true
}

function openEdit(k) {
  editing.value = k
  Object.assign(form, {
    name: k.name,
    quota: k.quota === null ? '' : String(k.quota),
    expires: k.expires_at ? toInputDate(k.expires_at - 1) : '',
  })
  formOpen.value = true
}

async function save() {
  const payload = {
    name: form.name,
    quota: form.quota === '' ? null : form.quota,
    expires_at: form.expires ? fromInputDate(form.expires, true) : null,
  }
  saving.value = true
  try {
    if (editing.value) {
      await api.patch(`/api/keys/${editing.value.id}`, payload)
      toast.success('已保存')
    } else {
      const data = await api.post('/api/keys', payload)
      createdKey.value = data.key
    }
    formOpen.value = false
    await load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

async function toggle(k) {
  const status = k.status === KeyStatus.ACTIVE ? KeyStatus.DISABLED : KeyStatus.ACTIVE
  try {
    await api.patch(`/api/keys/${k.id}`, { status })
    toast.success(status === KeyStatus.ACTIVE ? '已启用' : '已禁用')
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}

async function remove() {
  saving.value = true
  try {
    await api.del(`/api/keys/${removing.value.id}`)
    toast.success('已删除')
    removing.value = null
    await load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  refreshUser()
  await load()
  if (route.query.create) {
    router.replace({ query: {} })
    openCreate()
  }
})
</script>
