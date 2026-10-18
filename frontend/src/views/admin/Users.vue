<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-desc">查看用户余额与消费，调整余额、禁用账号或设置管理员。</p>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <form class="input-group has-prefix search" @submit.prevent="search">
          <span class="input-prefix"><Icon name="search" :size="15" /></span>
          <input v-model.trim="q" class="input input-sm" placeholder="搜索用户名或邮箱，回车确认" aria-label="搜索用户" />
        </form>
        <span class="muted">{{ num(total) }} 位用户</span>
      </div>
      <EmptyState v-if="!loading && !items.length" icon="users" title="没有找到用户" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>用户</th>
              <th class="right">余额</th>
              <th class="right">充值 / 消费</th>
              <th>注册 / 最近登录</th>
              <th class="actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in items" :key="u.id">
              <td class="nowrap">
                <div class="row" style="gap: 6px">
                  <span class="cell-main">{{ u.username }}</span>
                  <span v-if="u.role === 'admin'" class="badge badge-accent plain">管理员</span>
                  <span v-if="u.status !== 'active'" class="badge badge-danger">已禁用</span>
                </div>
                <div class="cell-sub">#{{ u.id }} · {{ u.email || '未填写邮箱' }} · {{ u.key_count }} 个密钥</div>
              </td>
              <td class="right num nowrap" :class="{ 'text-danger': u.balance <= 0 }"><b>{{ money(u.balance) }}</b></td>
              <td class="right num nowrap">
                <div class="text-success">+{{ money(u.total_recharge) }}</div>
                <div class="cell-sub">-{{ money(u.total_spent) }}</div>
              </td>
              <td class="nowrap">
                <div>{{ date(u.created_at) }}</div>
                <div class="cell-sub" :title="u.last_login_ip">{{ u.last_login_at ? `${relative(u.last_login_at)}登录` : '从未登录' }}</div>
              </td>
              <td class="actions">
                <button class="link-btn" @click="openAdjust(u)">调整余额</button>
                <button v-if="u.id !== store.user?.id" class="link-btn more" @click.stop="openMenu($event, u)">
                  更多<Icon name="chevron-down" :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total" class="card-footer">
        <Pagination :page="page" :total="total" :page-size="20" @change="load" />
      </div>
    </div>

    <Teleport to="body">
      <div v-if="menu" class="dropdown-menu" :style="menu.style" role="menu" @click.stop>
        <button class="dropdown-item" :class="{ danger: menu.user.status === 'active' }" @click="toggleStatus(menu.user)">
          <Icon :name="menu.user.status === 'active' ? 'lock' : 'check-circle'" :size="15" />
          {{ menu.user.status === 'active' ? '禁用账号' : '启用账号' }}
        </button>
        <button class="dropdown-item" @click="toggleRole(menu.user)">
          <Icon name="shield" :size="15" />{{ menu.user.role === 'admin' ? '取消管理员' : '设为管理员' }}
        </button>
      </div>
    </Teleport>

    <Modal :open="!!adjusting" title="调整余额" @close="adjusting = null">
      <form id="adjust-form" @submit.prevent="adjust">
        <p class="muted" style="margin-bottom: 14px">
          用户 <b style="color: var(--text)">{{ adjusting?.username }}</b> 当前余额 <b class="num" style="color: var(--text)">{{ money(adjusting?.balance || 0) }}</b>
        </p>
        <div class="field">
          <span class="field-label">操作</span>
          <div class="tabs">
            <button type="button" class="tab" :class="{ active: form.mode === 'add' }" @click="form.mode = 'add'">增加</button>
            <button type="button" class="tab" :class="{ active: form.mode === 'sub' }" @click="form.mode = 'sub'">扣减</button>
          </div>
        </div>
        <div class="field">
          <label for="adj-amount">金额</label>
          <div class="input-group has-prefix">
            <span class="input-prefix">{{ currency() }}</span>
            <input id="adj-amount" v-model="form.amount" class="input" type="number" min="0.01" step="0.01" required />
          </div>
          <div class="field-hint">线下收款后可在这里手动充值，会记录在用户的余额流水中。</div>
        </div>
        <div class="field">
          <label for="adj-note">备注</label>
          <input id="adj-note" v-model.trim="form.note" class="input" maxlength="100" placeholder="选填，用户可见" />
        </div>
      </form>
      <template #footer>
        <button class="btn" @click="adjusting = null">取消</button>
        <button class="btn btn-primary" form="adjust-form" :disabled="saving">确认{{ form.mode === 'add' ? '增加' : '扣减' }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import EmptyState from '../../components/EmptyState.vue'
import Icon from '../../components/Icon.vue'
import Modal from '../../components/Modal.vue'
import Pagination from '../../components/Pagination.vue'
import { api } from '../../api'
import { store } from '../../store'
import { currency, date, money, num, relative } from '../../format'
import { toast } from '../../toast'

const items = ref([])
const total = ref(0)
const page = ref(1)
const q = ref('')
const loading = ref(false)
const saving = ref(false)
const adjusting = ref(null)
const menu = ref(null)
const form = reactive({ mode: 'add', amount: '', note: '' })

// The table scrolls horizontally, so the row menu is teleported and fixed-positioned.
function openMenu(event, u) {
  if (menu.value?.user.id === u.id) return closeMenu()
  const rect = event.currentTarget.getBoundingClientRect()
  menu.value = {
    user: u,
    style: { position: 'fixed', top: `${rect.bottom + 6}px`, left: `${Math.max(8, rect.right - 160)}px`, right: 'auto', minWidth: '160px' },
  }
}
function closeMenu() {
  menu.value = null
}

async function load(p = page.value) {
  loading.value = true
  try {
    const data = await api.get('/api/admin/users', { page: p, q: q.value })
    items.value = data.items
    total.value = data.total
    page.value = data.page
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}
function search() {
  load(1)
}

function openAdjust(u) {
  adjusting.value = u
  Object.assign(form, { mode: 'add', amount: '', note: '' })
}

async function adjust() {
  const value = Number(form.amount)
  if (!(value > 0)) return toast.error('请输入大于 0 的金额')
  saving.value = true
  try {
    const amount = form.mode === 'add' ? value : -value
    const data = await api.post(`/api/admin/users/${adjusting.value.id}/balance`, { amount, note: form.note })
    toast.success(`已调整，当前余额 ${money(data.balance)}`)
    adjusting.value = null
    await load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

async function update(u, payload, message) {
  closeMenu()
  try {
    await api.patch(`/api/admin/users/${u.id}`, payload)
    toast.success(message)
    await load()
  } catch (e) {
    toast.error(e.message)
  }
}
function toggleStatus(u) {
  const status = u.status === 'active' ? 'banned' : 'active'
  update(u, { status }, status === 'active' ? '已启用' : '已禁用，该用户的密钥将停止工作')
}
function toggleRole(u) {
  const role = u.role === 'admin' ? 'user' : 'admin'
  update(u, { role }, role === 'admin' ? '已设为管理员' : '已取消管理员')
}

onMounted(() => {
  document.addEventListener('click', closeMenu)
  window.addEventListener('scroll', closeMenu, true)
  window.addEventListener('resize', closeMenu)
  load(1)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenu)
  window.removeEventListener('scroll', closeMenu, true)
  window.removeEventListener('resize', closeMenu)
})
</script>

<style scoped>
.search {
  width: 300px;
  max-width: 100%;
}
.search .input {
  padding-left: 32px;
}
.more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 12px;
}
</style>
