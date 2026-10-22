<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-desc">
          点击用户名查看密钥、余额流水和调用记录；按最近调用排序可找出长期不用的账号，勾选后批量移到不活跃。
        </p>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="row wrap">
          <div class="tabs">
            <button class="tab" :class="{ active: !archived }" @click="setArchived(false)">用户列表</button>
            <button class="tab" :class="{ active: archived }" @click="setArchived(true)">不活跃用户</button>
          </div>
          <form class="input-group has-prefix search" @submit.prevent="users.load(1)">
            <span class="input-prefix"><Icon name="search" :size="15" /></span>
            <input
              v-model.trim="q"
              class="input input-sm"
              placeholder="搜索用户名或邮箱，回车确认"
              aria-label="搜索用户"
            />
          </form>
        </div>
        <div v-if="selected.length" class="row batch-bar">
          <span class="muted">已选 {{ selected.length }} 位</span>
          <button type="button" class="btn btn-sm" :disabled="saving" @click="archiveSelected">
            <Icon name="archive" :size="15" />{{ archived ? '移回用户列表' : '移到不活跃' }}
          </button>
          <button type="button" class="btn btn-sm btn-ghost" @click="selected = []">取消选择</button>
        </div>
        <span v-else class="muted">{{ num(users.total) }} 位{{ archived ? '不活跃' : '' }}用户</span>
      </div>
      <div v-if="users.loading && !users.items.length" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState
        v-else-if="!users.items.length"
        icon="users"
        :title="archived ? '没有不活跃用户' : '没有找到用户'"
        :desc="archived ? '在用户列表中勾选用户后点击“移到不活跃”即可移入' : ''"
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th class="select-col">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  :indeterminate="selected.length > 0 && !allSelected"
                  aria-label="选择本页全部用户"
                  @change="selectAll($event.target.checked)"
                />
              </th>
              <th>用户</th>
              <th class="right"><SortButton field="balance" :sort="sort" @sort="setSort">余额</SortButton></th>
              <th class="right">
                <SortButton field="recharge" :sort="sort" @sort="setSort">充值</SortButton> /
                <SortButton field="spent" :sort="sort" @sort="setSort">消费</SortButton>
              </th>
              <th><SortButton field="last_used" :sort="sort" @sort="setSort">最近调用</SortButton></th>
              <th>
                <SortButton field="created" :sort="sort" @sort="setSort">注册</SortButton> /
                <SortButton field="last_login" :sort="sort" @sort="setSort">最近登录</SortButton>
              </th>
              <th class="actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users.items" :key="u.id">
              <td class="select-col">
                <input v-model="selected" type="checkbox" :value="u.id" :aria-label="`选择 ${u.username}`" />
              </td>
              <td class="nowrap">
                <div class="row" style="gap: 6px">
                  <button
                    type="button"
                    class="link-btn cell-main user-link"
                    :aria-label="`查看 ${u.username} 的详情`"
                    @click="openDetail(u)"
                  >
                    {{ u.username }}
                  </button>
                  <StatusBadge v-if="u.role === Role.ADMIN" class="plain" :map="ROLES" :value="u.role" />
                  <StatusBadge v-if="u.status !== UserStatus.ACTIVE" :map="USER_STATUSES" :value="u.status" />
                </div>
                <div class="cell-sub">
                  #{{ u.id }} · {{ u.email || '未填写邮箱' }} ·
                  <button type="button" class="link-btn" @click="openDetail(u)">{{ u.key_count }} 个密钥</button>
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
                <span v-if="u.last_used_at" :title="dateTime(u.last_used_at)">{{ relative(u.last_used_at) }}</span>
                <span v-else class="faint">从未调用</span>
              </td>
              <td class="nowrap">
                <div>{{ date(u.created_at) }}</div>
                <div class="cell-sub" :title="u.last_login_ip">
                  {{ u.last_login_at ? `${relative(u.last_login_at)}登录` : '从未登录' }}
                </div>
              </td>
              <td class="actions">
                <button class="link-btn" @click="openAdjust(u)">调整余额</button>
                <button v-if="u.id !== store.user?.id" class="link-btn more" @click="openMenu($event, u)">
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
      <div v-if="menu.open" ref="menuPanel" class="dropdown-menu" :style="menu.style" role="menu">
        <button
          class="dropdown-item"
          :class="{ danger: menuUser.status === UserStatus.ACTIVE }"
          @click="toggleStatus(menuUser)"
        >
          <Icon :name="menuUser.status === UserStatus.ACTIVE ? 'lock' : 'check-circle'" :size="15" />
          {{ menuUser.status === UserStatus.ACTIVE ? '禁用账号' : '启用账号' }}
        </button>
        <button class="dropdown-item" @click="openReset(menuUser)"><Icon name="key" :size="15" />重置密码</button>
        <button class="dropdown-item" @click="toggleRole(menuUser)">
          <Icon name="shield" :size="15" />{{ menuUser.role === Role.ADMIN ? '取消管理员' : '设为管理员' }}
        </button>
      </div>
    </Teleport>

    <UserDetailModal
      v-if="detailUser"
      :key="detailUser.id"
      :user="detailUser"
      @close="detailUser = null"
      @deleted="users.load()"
    />

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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Modal from '@/components/base/Modal.vue'
import Pagination from '@/components/base/Pagination.vue'
import SortButton from '@/components/base/SortButton.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import UserDetailModal from '@/components/admin/UserDetailModal.vue'
import { accountsApi } from '@/api/accounts'
import { billingApi } from '@/api/billing'
import { usePagedList } from '@/composables/usePagedList'
import { usePopover } from '@/composables/usePopover'
import { REDEEM_TYPES, RedeemType, ROLES, Role, USER_STATUSES, UserStatus } from '@/constants'
import { store } from '@/store'
import { currency, date, dateTime, money, num, relative } from '@/utils/format'
import { toast } from '@/toast'

const q = ref('')
const archived = ref(false)
const sort = reactive({ key: 'created', desc: true })
const users = usePagedList(accountsApi.adminListUsers, () => ({
  q: q.value,
  archived: archived.value ? 1 : '',
  sort: sort.key,
  order: sort.desc ? 'desc' : 'asc',
}))
const selected = ref([])
const allSelected = computed(() => users.items.length > 0 && users.items.every((u) => selected.value.includes(u.id)))
const saving = ref(false)
const adjusting = ref(null)
const detailUser = ref(null)
const resetting = ref(null)
const newPassword = ref('')
const showPassword = ref(false)
const form = reactive({ mode: 'add', type: '', amount: '', note: '' })

// The table scrolls horizontally, so the row menu is teleported and placed by its button.
const menuPanel = ref(null)
const menuUser = ref(null)
const menu = usePopover({
  panel: menuPanel,
  place: (rect) => ({
    position: 'fixed',
    top: `${rect.bottom + 6}px`,
    left: `${Math.max(8, rect.right - 160)}px`,
    right: 'auto',
    minWidth: '160px',
  }),
})
function openMenu(event, u) {
  menuUser.value = u
  menu.toggle(event)
}

// A reload keeps only the selected rows that are still on screen.
watch(
  () => users.items,
  (items) => {
    selected.value = selected.value.filter((id) => items.some((u) => u.id === id))
  },
)

function selectAll(checked) {
  selected.value = checked ? users.items.map((u) => u.id) : []
}

function setSort(key) {
  if (sort.key === key) sort.desc = !sort.desc
  else Object.assign(sort, { key, desc: true })
  users.load(1)
}

// Rows moved out of this tab shrink the list, so stay within the pages that remain.
function pageAfterRemoving(count) {
  return Math.min(users.page, Math.max(1, Math.ceil((users.total - count) / users.page_size)))
}

async function archiveSelected() {
  if (saving.value || !selected.value.length) return
  const value = !archived.value
  const page = pageAfterRemoving(selected.value.length)
  saving.value = true
  try {
    const { updated } = await accountsApi.adminArchiveUsers({ ids: selected.value, archived: value })
    toast.success(value ? `已将 ${updated} 位用户移到不活跃` : `已将 ${updated} 位用户移回用户列表`)
    selected.value = []
    await users.load(page)
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

function openDetail(u) {
  menu.close()
  detailUser.value = u
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
    const data = await billingApi.adminAdjustBalance(adjusting.value.id, payload)
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
  menu.close()
  resetting.value = u
  newPassword.value = ''
  showPassword.value = false
}

async function resetPassword() {
  if (saving.value) return
  if (newPassword.value.length < 8) return toast.error('密码至少 8 位')
  saving.value = true
  try {
    await accountsApi.adminResetPassword(resetting.value.id, { password: newPassword.value })
    toast.success(`已重置 ${resetting.value.username} 的密码`)
    resetting.value = null
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

function setArchived(value) {
  if (archived.value === value) return
  menu.close()
  archived.value = value
  users.items = []
  users.load(1)
}

async function runMenuAction(request, message) {
  menu.close()
  try {
    await request()
    toast.success(message)
    await users.load()
  } catch (e) {
    toast.error(e.message)
  }
}
function toggleStatus(u) {
  const status = u.status === UserStatus.ACTIVE ? UserStatus.BANNED : UserStatus.ACTIVE
  runMenuAction(
    () => accountsApi.adminSetUserStatus(u.id, { status }),
    status === UserStatus.ACTIVE ? '已启用' : '已禁用，该用户的密钥将停止工作',
  )
}
function toggleRole(u) {
  const role = u.role === Role.ADMIN ? Role.USER : Role.ADMIN
  runMenuAction(
    () => accountsApi.adminSetUserRole(u.id, { role }),
    role === Role.ADMIN ? '已设为管理员' : '已取消管理员',
  )
}

onMounted(() => users.load(1))
</script>

<style scoped>
.search {
  width: 300px;
  max-width: 100%;
}
.search .input {
  padding-left: 32px;
}
.user-link {
  color: var(--text);
}
.user-link:hover {
  color: var(--accent);
}
.select-col {
  width: 1%;
  padding-right: 0;
}
.select-col input {
  display: block;
  accent-color: var(--accent);
  cursor: pointer;
}
.batch-bar {
  gap: 8px;
}
.more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 12px;
}
</style>
