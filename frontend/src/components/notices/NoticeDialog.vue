<template>
  <Modal open title="公告中心" wide @close="emit('close')">
    <template #header>
      <div class="notice-header">
        <span class="notice-header-icon"><Icon name="megaphone" :size="20" /></span>
        <div class="modal-title">公告中心</div>
      </div>
    </template>

    <div class="notice-toolbar">
      <div v-if="days.length" class="notice-tabs" aria-label="公告筛选">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="notice-tab"
          :class="{ active: mode === tab.key }"
          :aria-pressed="mode === tab.key"
          @click="setMode(tab.key)"
        >
          {{ tab.label }}
          <span v-if="tab.count" class="notice-tab-count">{{ tab.count }}</span>
        </button>
      </div>
      <button v-if="isAdmin && !composing" class="btn notice-new" @click="startCompose">
        <Icon name="plus" :size="16" />发布公告
      </button>
    </div>

    <NoticeEditor
      v-if="composing"
      v-model="composeDraft"
      class="notice-compose"
      submit-label="发布"
      hint="发布后，所有用户右上角的通知图标会出现红点"
      :saving="notices.saving"
      @submit="publish"
      @cancel="composing = false"
    />

    <div v-if="notices.loading" class="stack" style="gap: 10px">
      <div v-for="i in 3" :key="i" class="skeleton" style="height: 64px" />
    </div>
    <EmptyState v-else-if="!days.length" icon="bell" title="暂无公告" />
    <EmptyState
      v-else-if="!groups.length"
      icon="calendar"
      title="本周还没有发布公告"
      desc="点击「全部」查看更早的公告"
    />
    <div
      v-else
      ref="scroller"
      class="notice-scroll"
      :style="listHeight && { maxHeight: `min(${listHeight}px, 52vh)` }"
      @scroll="updateMore"
    >
      <div>
        <div v-if="mode === 'all'" class="notice-date">
          <NoticeDatePicker ref="datePicker" v-model="selectedKey" :days="days" @open="activeItemId = null" />
        </div>
        <section v-for="group in groups" :key="group.key" class="notice-group">
          <div v-if="mode !== 'all'" class="notice-date">
            {{ group.displayDate }}
          </div>
          <ol class="notice-list">
            <NoticeItem
              v-for="notice in group.items"
              :key="notice.id"
              :notice="notice"
              :unread="notice.created_at > notices.seenBefore"
              :is-admin="isAdmin"
              :saving="notices.saving"
              :editing="editingId === notice.id"
              :active="activeItemId === notice.id"
              @activate="activateItem(notice.id)"
              @edit="startEdit(notice.id)"
              @save="saveEdit(notice.id, $event)"
              @cancel-edit="editingId = null"
              @remove="remove(notice.id)"
            />
          </ol>
        </section>
      </div>
    </div>

    <template #footer>
      <div class="notice-footer">
        <span class="notice-footer-hint">
          {{ notices.loading ? '正在加载公告…' : `共 ${visibleCount} 条公告` }}
          <span v-if="hasMore && !notices.loading"> · 向下滚动查看更多</span>
        </span>
        <button class="btn btn-primary" @click="emit('close')">关闭</button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Modal from '@/components/base/Modal.vue'
import { Role } from '@/constants'
import { store } from '@/store'
import { date } from '@/utils/format'
import NoticeDatePicker from './NoticeDatePicker.vue'
import NoticeEditor from './NoticeEditor.vue'
import NoticeItem from './NoticeItem.vue'

// The bell owns this controller so read state survives closing the dialog.
const props = defineProps({ notices: { type: Object, required: true } })
const emit = defineEmits(['close'])
const DAY_MS = 86400000
const WEEKDAYS = '日一二三四五六'
const MAX_VISIBLE = 5
const mode = ref('latest')
const selectedKey = ref('')
const composing = ref(false)
const composeDraft = ref('')
const editingId = ref(null)
const activeItemId = ref(null)
const datePicker = ref(null)
const isAdmin = computed(() => store.user?.role === Role.ADMIN)

// Notices arrive newest first. Each day also carries the labels used by the picker.
const days = computed(() => {
  const result = []
  for (const notice of props.notices.items) {
    const key = date(notice.created_at)
    if (result.at(-1)?.key !== key) {
      result.push({ key, items: [], label: dayTitle(key), caption: weekdayOf(key), displayDate: groupDate(key) })
    }
    result.at(-1).items.push(notice)
  }
  return result
})
const weekDays = computed(() => days.value.filter((day) => day.items[0].created_at >= weekStart()))
const groups = computed(() => {
  if (mode.value === 'week') return weekDays.value
  if (mode.value === 'all')
    return [days.value.find((day) => day.key === selectedKey.value) || days.value[0]].filter(Boolean)
  return days.value.slice(0, 1)
})
const visibleCount = computed(() => groups.value.reduce((sum, group) => sum + group.items.length, 0))
const tabs = computed(() => [
  { key: 'latest', label: days.value[0]?.label || '最新', count: days.value[0]?.items.length || 0 },
  { key: 'week', label: '本周', count: weekDays.value.reduce((sum, day) => sum + day.items.length, 0) },
  { key: 'all', label: '全部' },
])

// Weeks start on Monday.
function weekStart() {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return d.getTime()
}
function dayTitle(key) {
  if (key === date(Date.now())) return '今天'
  if (key === date(Date.now() - DAY_MS)) return '昨天'
  const [y, m, d] = key.split('-').map(Number)
  return `${y === new Date().getFullYear() ? '' : `${y}年`}${m}月${d}日`
}
function groupDate(key) {
  const [y, m, d] = key.split('-').map(Number)
  const prefix = dayTitle(key).endsWith('天') ? `${dayTitle(key)} · ` : ''
  return `${prefix}${y === new Date().getFullYear() ? '' : `${y}年`}${m}月${d}日 · 星期${WEEKDAYS[new Date(y, m - 1, d).getDay()]}`
}
function weekdayOf(key) {
  const [y, m, d] = key.split('-').map(Number)
  const weekday = `星期${WEEKDAYS[new Date(y, m - 1, d).getDay()]}`
  // 今天 and 昨天 do not say which date it is, so add it.
  return dayTitle(key).endsWith('天') ? `${m}月${d}日 ${weekday}` : weekday
}

// Show at most five notices at a time and scroll the rest. Rows vary in height, so measure where
// the fifth one ends rather than assume a fixed height; the observer re-measures whenever the list
// changes size (another tab or day, an edit box opening, the window resizing).
const scroller = ref(null)
const listHeight = ref(null)
const hasMore = ref(false)
function fitList() {
  const el = scroller.value
  if (!el) {
    hasMore.value = false
    listHeight.value = null
    return
  }
  const items = el.querySelectorAll('.notice-item')
  const last = items[MAX_VISIBLE - 1]
  listHeight.value = items.length > MAX_VISIBLE ? last.offsetTop + last.offsetHeight + 4 : null
  nextTick(updateMore)
}
function updateMore() {
  const el = scroller.value
  hasMore.value = !!el && el.scrollTop + el.clientHeight < el.scrollHeight - 4
}
watch(
  scroller,
  (el, _, onCleanup) => {
    if (!el) {
      hasMore.value = false
      listHeight.value = null
      return
    }
    const observer = new ResizeObserver(fitList)
    observer.observe(el.firstElementChild)
    observer.observe(el)
    onCleanup(() => observer.disconnect())
  },
  { flush: 'post' },
)
watch([mode, selectedKey], () => {
  editingId.value = null
  activeItemId.value = null
  datePicker.value?.close()
  if (scroller.value) scroller.value.scrollTop = 0
})

function setMode(key) {
  mode.value = key
  editingId.value = null
  activeItemId.value = null
  datePicker.value?.close()
}
function activateItem(id) {
  activeItemId.value = id
  datePicker.value?.close()
}
function startCompose() {
  activeItemId.value = null
  editingId.value = null
  composeDraft.value = ''
  composing.value = true
}
async function publish(content) {
  const notice = await props.notices.create(content)
  if (!notice) return
  selectedKey.value = date(notice.created_at)
  mode.value = 'latest'
  composing.value = false
}
function startEdit(id) {
  activeItemId.value = null
  composing.value = false
  editingId.value = id
}
async function saveEdit(id, content) {
  if (await props.notices.update(id, content)) editingId.value = null
}
async function remove(id) {
  if (await props.notices.remove(id)) activeItemId.value = null
}
</script>

<style scoped>
.notice-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}
.notice-header-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--accent-soft);
  color: var(--accent);
}
.notice-header .modal-title {
  font-size: 20px;
  letter-spacing: -0.03em;
}
.notice-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  column-gap: 16px;
  row-gap: 10px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--border);
}
.notice-tabs {
  display: flex;
  gap: 24px;
}
.notice-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 44px;
  padding: 0 2px;
  margin-bottom: -1px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--muted);
  font-weight: 500;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}
.notice-tab:hover {
  color: var(--text);
}
.notice-tab.active {
  border-bottom-color: var(--accent);
  color: var(--accent-text);
}
.notice-tab-count {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  opacity: 0.75;
}
.notice-new {
  min-height: 30px;
  margin: 0 0 8px auto;
  padding: 5px 10px;
  font-size: 12px;
  box-shadow: none;
}

.notice-compose {
  margin-bottom: 16px;
}
/* Keep row measurements relative to the scrolling list (see fitList). */
.notice-scroll {
  position: relative;
  margin-right: -8px;
  padding-right: 8px;
  max-height: 52vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
}
.notice-group + .notice-group {
  margin-top: 20px;
}
.notice-date {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0 12px;
  background: var(--surface);
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
}
.notice-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.notice-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.notice-footer-hint {
  color: var(--muted);
  font-size: 12px;
}
.notice-footer > button {
  flex: none;
  min-width: 76px;
}

@media (max-width: 480px) {
  .notice-tabs {
    gap: 18px;
  }
  .notice-new {
    margin-top: 4px;
  }
}
</style>
