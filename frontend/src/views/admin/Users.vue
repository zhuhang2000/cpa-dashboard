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
        <form class="input-group has-prefix search" @submit.prevent="users.load(1)">
          <span class="input-prefix"><Icon name="search" :size="15" /></span>
          <input
            v-model.trim="q"
            class="input input-sm"
            placeholder="搜索用户名或邮箱，回车确认"
            aria-label="搜索用户"
          />
        </form>
        <span class="muted">{{ num(users.total) }} 位用户</span>
      </div>
      <div v-if="users.loading && !users.items.length" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState v-else-if="!users.items.length" icon="users" title="没有找到用户" />
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
            <tr v-for="u in users.items" :key="u.id">
              <td class="nowrap">
                <div class="row" style="gap: 6px">
                  <span class="cell-main">{{ u.username }}</span>
                  <StatusBadge v-if="u.role === Role.ADMIN" class="plain" :map="ROLES" :value="u.role" />
                  <StatusBadge v-if="u.status !== UserStatus.ACTIVE" :map="USER_STATUSES" :value="u.status" />
                </div>
                <div class="cell-sub">#{{ u.id }} · {{ u.email || '未填写邮箱' }} · {{ u.key_count }} 个密钥</div>
              </td>
              <td class="right num nowrap" :class="{ 'text-danger': u.balance <= 0 }">
                <b>{{ money(u.balance) }}</b>
              </td>
              <td class="right num nowrap">
                <div class="text-success">+{{ money(u.total_recharge) }}</div>
                <div class="cell-sub">-{{ money(u.total_spent) }}</div>
              </td>
              <td class="nowrap">
                <div>{{ date(u.created_at) }}</div>
                <div class="cell-sub" :title="u.last_login_ip">
                  {{ u.last_login_at ? `${relative(u.last_login_at)}登录` : '从未登录' }}
                </div>
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
      <div v-if="users.total" class="card-footer">
        <Pagination :page="users.page" :total="users.total" :page-size="users.page_size" @change="users.load" />
      </div>
    </div>

    <Teleport to="body">
      <div v-if="menu" class="dropdown-menu" :style="menu.style" role="menu" @click.stop>
        <button
          class="dropdown-item"
          :class="{ danger: menu.user.status === UserStatus.ACTIVE }"
          @click="toggleStatus(menu.user)"
        >
          <Icon :name="menu.user.status === UserStatus.ACTIVE ? 'lock' : 'check-circle'" :size="15" />
          {{ menu.user.status === UserStatus.ACTIVE ? '禁用账号' : '启用账号' }}
        </button>
        <button class="dropdown-item" @click="toggleRole(menu.user)">
          <Icon name="shield" :size="15" />{{ menu.user.role === Role.ADMIN ? '取消管理员' : '设为管理员' }}
        </button>
      </div>
    </Teleport>

    <Modal :open="!!adjusting" title="调整余额" @close="adjusting = null">
      <form id="adjust-form" @submit.prevent="adjust">
        <p class="muted" style="margin-bottom: 14px">
          用户 <b style="color: var(--text)">{{ adjusting?.username }}</b> 当前余额
          <b class="num" style="color: var(--text)">{{ money(adjusting?.balance || 0) }}</b>
        </p>
        <div class="field">
          <span class="field-label">操作</span>
          <div class="tabs">
            <button type="button" class="tab" :class="{ active: form.mode === 'add' }" @click="form.mode = 'add'">
              增加
            </button>
            <button type="button" class="tab" :class="{ active: form.mode === 'sub' }" @click="form.mode = 'sub'">
              扣减
            </button>
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
        <button class="btn btn-primary" form="adjust-form" :disabled="saving">
          确认{{ form.mode === 'add' ? '增加' : '扣减' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import Modal from '@/components/Modal.vue'
import Pagination from '@/components/Pagination.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api'
import { usePagedList } from '@/composables/usePagedList'
import { ROLES, Role, USER_STATUSES, UserStatus } from '@/constants'
import { store } from '@/store'
import { currency, date, money, num, relative } from '@/utils/format'
import { toast } from '@/toast'

const q = ref('')
const users = usePagedList('/api/admin/users', () => ({ q: q.value }))
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
    style: {
      position: 'fixed',
      top: `${rect.bottom + 6}px`,
      left: `${Math.max(8, rect.right - 160)}px`,
      right: 'auto',
      minWidth: '160px',
    },
  }
}
function closeMenu() {
  menu.value = null
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
    await users.load()
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
    await users.load()
  } catch (e) {
    toast.error(e.message)
  }
}
function toggleStatus(u) {
  const status = u.status === UserStatus.ACTIVE ? UserStatus.BANNED : UserStatus.ACTIVE
  update(u, { status }, status === UserStatus.ACTIVE ? '已启用' : '已禁用，该用户的密钥将停止工作')
}
function toggleRole(u) {
  const role = u.role === Role.ADMIN ? Role.USER : Role.ADMIN
  update(u, { role }, role === Role.ADMIN ? '已设为管理员' : '已取消管理员')
}

onMounted(() => {
  document.addEventListener('click', closeMenu)
  window.addEventListener('scroll', closeMenu, true)
  window.addEventListener('resize', closeMenu)
  users.load(1)
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
