<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-desc">查看用户余额与消费，点击用户名查看 API 密钥，可调整余额、重置密码、禁用账号或设置管理员。</p>
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
                  <button
                    type="button"
                    class="link-btn cell-main user-keys-link"
                    :aria-label="`查看 ${u.username} 的 API 密钥`"
                    @click="openKeys(u)"
                  >
                    {{ u.username }}
                  </button>
                  <StatusBadge v-if="u.role === Role.ADMIN" class="plain" :map="ROLES" :value="u.role" />
                  <StatusBadge v-if="u.status !== UserStatus.ACTIVE" :map="USER_STATUSES" :value="u.status" />
                </div>
                <div class="cell-sub">
                  #{{ u.id }} · {{ u.email || '未填写邮箱' }} ·
                  <button type="button" class="link-btn" @click="openKeys(u)">{{ u.key_count }} 个密钥</button>
                </div>
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
        <button class="dropdown-item" @click="openReset(menu.user)">
          <Icon name="key" :size="15" />重置密码
        </button>
        <button class="dropdown-item" @click="toggleRole(menu.user)">
          <Icon name="shield" :size="15" />{{ menu.user.role === Role.ADMIN ? '取消管理员' : '设为管理员' }}
        </button>
      </div>
    </Teleport>

    <UserKeysModal v-if="keyUser" :key="keyUser.id" :user="keyUser" @close="keyUser = null" @deleted="users.load()" />

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
        <div v-if="form.mode === 'add'" class="field">
          <label for="adj-type">类型</label>
          <select id="adj-type" v-model="form.type" class="select" required>
            <option disabled value="">请选择类型</option>
            <option v-for="(entry, value) in REDEEM_TYPES" :key="value" :value="value">{{ entry.label }}</option>
          </select>
        </div>
        <div class="field">
          <label for="adj-amount">金额</label>
          <div class="input-group has-prefix">
            <span class="input-prefix">{{ currency() }}</span>
            <input id="adj-amount" v-model="form.amount" class="input" type="number" min="0.01" step="0.01" required />
          </div>
          <div class="field-hint">
            {{
              form.mode === 'sub'
                ? '扣减余额，不抵扣充值统计，也不计入调用消费。'
                : !form.type
                  ? '请选择充值或赠送。'
                  : form.type === RedeemType.GIFT
                    ? '赠送仅增加余额，不计入充值统计。'
                    : '充值增加余额，并计入充值统计。'
            }}
          </div>
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

    <Modal :open="!!resetting" title="重置密码" @close="resetting = null">
      <form id="reset-form" @submit.prevent="resetPassword">
        <p class="muted" style="margin-bottom: 14px">
          为用户 <b style="color: var(--text)">{{ resetting?.username }}</b> 设置新密码，重置后该用户需重新登录。
        </p>
        <div class="field">
          <label for="reset-pass">新密码</label>
          <div class="input-group">
            <input
              id="reset-pass"
              v-model="newPassword"
              class="input"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              minlength="8"
              maxlength="128"
              placeholder="至少 8 位"
              required
            />
            <button
              type="button"
              class="input-addon"
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              @click="showPassword = !showPassword"
            >
              <Icon :name="showPassword ? 'eye-off' : 'eye'" :size="16" />
            </button>
          </div>
          <div class="field-hint">请通过安全渠道将新密码告知用户，并提醒其登录后在个人设置中修改。</div>
        </div>
      </form>
      <template #footer>
        <button class="btn" @click="resetting = null">取消</button>
        <button class="btn btn-primary" form="reset-form" :disabled="saving">确认重置</button>
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
import UserKeysModal from '@/components/admin/UserKeysModal.vue'
import { accountsApi } from '@/api/accounts'
import { billingApi } from '@/api/billing'
import { usePagedList } from '@/composables/usePagedList'
import { REDEEM_TYPES, RedeemType, ROLES, Role, USER_STATUSES, UserStatus } from '@/constants'
import { store } from '@/store'
import { currency, date, money, num, relative } from '@/utils/format'
import { toast } from '@/toast'

const q = ref('')
const users = usePagedList(accountsApi.listUsers, () => ({ q: q.value }))
const saving = ref(false)
const adjusting = ref(null)
const keyUser = ref(null)
const menu = ref(null)
const resetting = ref(null)
const newPassword = ref('')
const showPassword = ref(false)
const form = reactive({ mode: 'add', type: '', amount: '', note: '' })

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

function openKeys(u) {
  closeMenu()
  keyUser.value = u
}

function openAdjust(u) {
  adjusting.value = u
  Object.assign(form, { mode: 'add', type: '', amount: '', note: '' })
}

async function adjust() {
  if (saving.value) return
  if (form.mode === 'add' && !form.type) return toast.error('请选择充值或赠送')
  const value = Number(form.amount)
  if (!(value > 0)) return toast.error('请输入大于 0 的金额')
  saving.value = true
  try {
    const amount = form.mode === 'add' ? value : -value
    const payload = { amount, note: form.note }
    if (form.mode === 'add') payload.type = form.type
    const data = await billingApi.adjustBalance(adjusting.value.id, payload)
    toast.success(`已调整，当前余额 ${money(data.balance)}`)
    adjusting.value = null
    await users.load()
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

function openReset(u) {
  closeMenu()
  resetting.value = u
  newPassword.value = ''
  showPassword.value = false
}

async function resetPassword() {
  if (saving.value) return
  if (newPassword.value.length < 8) return toast.error('密码至少 8 位')
  saving.value = true
  try {
    await accountsApi.resetPassword(resetting.value.id, { password: newPassword.value })
    toast.success(`已重置 ${resetting.value.username} 的密码`)
    resetting.value = null
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

async function update(u, payload, message) {
  closeMenu()
  try {
    await accountsApi.updateUser(u.id, payload)
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
.user-keys-link {
  color: var(--text);
}
.user-keys-link:hover {
  color: var(--accent);
}
.more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 12px;
}
</style>
