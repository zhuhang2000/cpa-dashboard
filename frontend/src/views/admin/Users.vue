<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p v-if="isAdmin" class="page-desc">
          点击用户名查看密钥、余额流水和调用记录；按最近调用排序可找出长期不用的账号，勾选后可批量移到不活跃或设置标签。
        </p>
        <p v-else class="page-desc">
          这里列出由你负责的用户，你可以为他们充值或扣款，点击用户名查看余额流水和调用记录。
        </p>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div v-if="isAdmin" class="tabs">
          <button class="tab" :class="{ active: !archived }" @click="setArchived(false)">用户列表</button>
          <button class="tab" :class="{ active: archived }" @click="setArchived(true)">不活跃用户</button>
        </div>
        <div class="row wrap header-actions">
          <div v-if="selected.length" class="row batch-bar">
            <span class="muted">已选 {{ selected.length }} 位</span>
            <button type="button" class="btn btn-sm" :disabled="saving" @click="archiveSelected">
              <Icon name="archive" :size="15" />{{ archived ? '移回用户列表' : '移到不活跃' }}
            </button>
            <button type="button" class="btn btn-sm" :disabled="saving" @click="openTagging">
              <Icon name="tag" :size="15" />设置标签
            </button>
            <button type="button" class="btn btn-sm btn-ghost" @click="selected = []">取消选择</button>
          </div>
          <SearchInput
            v-model="q"
            :placeholder="isAdmin ? '搜索用户名、邮箱或标签，回车确认' : '搜索用户名或邮箱，回车确认'"
            label="搜索用户"
            style="width: 300px"
            @search="users.load(1)"
          />
        </div>
      </div>
      <div v-if="users.loading && !users.items.length" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState
        v-else-if="!users.items.length"
        icon="users"
        :title="archived ? '没有不活跃用户' : '没有找到用户'"
        :desc="emptyDesc"
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th v-if="isAdmin" class="select-col">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  :indeterminate="selected.length > 0 && !allSelected"
                  :disabled="!regularIds.length"
                  aria-label="选择本页全部普通用户"
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
              <td v-if="isAdmin" class="select-col">
                <input
                  v-if="u.role === Role.USER"
                  v-model="selected"
                  type="checkbox"
                  :value="u.id"
                  :aria-label="`选择 ${u.username}`"
                />
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
                  <StatusBadge v-if="u.role !== Role.USER" class="plain" :map="ROLES" :value="u.role" />
                  <span
                    v-if="isAdmin && u.tag"
                    class="badge plain"
                    :title="u.role === Role.MANAGER ? '负责的标签' : '所属标签'"
                  >
                    <Icon name="tag" :size="12" />{{ u.tag }}
                  </span>
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
                <button class="link-btn" @click="adjusting = u">调整余额</button>
                <button v-if="isAdmin && u.id !== store.user?.id" class="link-btn more" @click="openMenu($event, u)">
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
        <button class="dropdown-item" @click="openRole(menuUser)"><Icon name="shield" :size="15" />设置身份</button>
      </div>
    </Teleport>

    <UserDetailModal
      v-if="detailUser"
      :key="detailUser.id"
      :user="detailUser"
      @close="detailUser = null"
      @deleted="users.load()"
    />
    <UserBalanceModal v-if="adjusting" :user="adjusting" @close="adjusting = null" @saved="users.load()" />
    <UserPasswordModal v-if="resetting" :user="resetting" @close="resetting = null" />
    <UserRoleModal v-if="assigning" :user="assigning" @close="assigning = null" @saved="users.load()" />
    <UserTagModal v-if="tagging" :ids="tagging" @close="tagging = null" @saved="afterTagging" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Pagination from '@/components/base/Pagination.vue'
import SearchInput from '@/components/base/SearchInput.vue'
import SortButton from '@/components/base/SortButton.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import UserBalanceModal from '@/components/admin/UserBalanceModal.vue'
import UserDetailModal from '@/components/admin/UserDetailModal.vue'
import UserPasswordModal from '@/components/admin/UserPasswordModal.vue'
import UserRoleModal from '@/components/admin/UserRoleModal.vue'
import UserTagModal from '@/components/admin/UserTagModal.vue'
import { accountsApi } from '@/api/accounts'
import { usePagedList } from '@/composables/usePagedList'
import { usePopover } from '@/composables/usePopover'
import { ROLES, Role, USER_STATUSES, UserStatus } from '@/constants'
import { store } from '@/store'
import { date, dateTime, money, relative } from '@/utils/format'
import { toast } from '@/toast'

// Tag managers share this page: the API lists only their users and never names their tag, and only the
// system administrator gets the selection, the inactive tab and the row menu (gifts: UserBalanceModal).
const isAdmin = computed(() => store.user?.role === Role.ADMIN)
const q = ref('')
const archived = ref(false)
const sort = reactive({ key: 'created', desc: true })
const users = usePagedList(accountsApi.adminListUsers, () => ({
  q: q.value,
  archived: archived.value ? 1 : '',
  sort: sort.key,
  order: sort.desc ? 'desc' : 'asc',
}))
const emptyDesc = computed(() => {
  if (archived.value) return '在用户列表中勾选用户后点击“移到不活跃”即可移入'
  if (!isAdmin.value && !q.value) return '超级管理员把用户分配给你后，他们会显示在这里'
  return ''
})
const selected = ref([])
// Only regular users can be selected: the batch actions are for them, while administrators and
// managers are handled one at a time from the row menu.
const regularIds = computed(() => users.items.filter((u) => u.role === Role.USER).map((u) => u.id))
const allSelected = computed(
  () => regularIds.value.length > 0 && regularIds.value.every((id) => selected.value.includes(id)),
)
const saving = ref(false) // archiving the selection
// What each dialog works on; a dialog is mounted only while it has something.
const detailUser = ref(null)
const adjusting = ref(null)
const resetting = ref(null)
const assigning = ref(null)
const tagging = ref(null) // the ids of the users being tagged

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

// A reload keeps only the selected users still on screen, and still regular users.
watch(regularIds, (ids) => {
  selected.value = selected.value.filter((id) => ids.includes(id))
})

function selectAll(checked) {
  selected.value = checked ? [...regularIds.value] : []
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

function openReset(u) {
  menu.close()
  resetting.value = u
}

function openRole(u) {
  menu.close()
  assigning.value = u
}

function openTagging() {
  tagging.value = [...selected.value]
}

// Tagged users leave the selection, as after archiving.
function afterTagging() {
  selected.value = []
  users.load()
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

onMounted(() => users.load(1))
</script>

<style scoped>
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
/* The batch actions and the search keep to the right, with or without the tabs on the left. */
.header-actions {
  gap: 12px;
  margin-left: auto;
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
