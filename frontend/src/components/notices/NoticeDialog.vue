<template>
  <Modal :open="open && !selected" wide title="公告" @close="emit('close')">
    <template #header>
      <div class="notice-header">
        <span class="notice-header-icon"><Icon name="bell" :size="19" /></span>
        <div>
          <div class="modal-title">公告</div>
          <div class="notice-subtitle">
            <template v-if="notices.unreadCount">
              <span class="notice-unread-num num">{{ notices.unreadCount }}</span> 未读
            </template>
            <template v-else>共 {{ notices.items.length }} 条公告</template>
          </div>
        </div>
        <div class="notice-header-actions">
          <button v-if="sessionStore.isAdmin && !composing" class="btn btn-sm" @click="startCompose">
            <Icon name="plus" :size="15" />发布公告
          </button>
          <button v-if="notices.unreadCount" class="btn btn-primary btn-sm" @click="notices.markAllRead">
            全部已读
          </button>
        </div>
      </div>
    </template>

    <NoticeEditor
      v-if="composing"
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
    <EmptyState v-else-if="!notices.items.length" icon="bell" title="暂无公告" />
    <div v-else ref="scroller" class="notice-scroll">
      <ol class="notice-list">
        <NoticeItem
          v-for="notice in notices.items"
          :key="notice.id"
          :notice="notice"
          :title="noticeTitle(notice)"
          :unread="!notices.isRead(notice)"
          :is-admin="sessionStore.isAdmin"
          :saving="notices.saving"
          :editing="editingId === notice.id"
          :active="activeItemId === notice.id"
          @select="openDetail(notice)"
          @activate="activeItemId = notice.id"
          @edit="startEdit(notice.id)"
          @save="saveEdit(notice.id, $event)"
          @cancel-edit="editingId = null"
          @remove="notices.remove(notice.id)"
        />
      </ol>
    </div>

    <template #footer>
      <div class="notice-footer">
        <span class="notice-footer-hint">
          {{ notices.loading ? '正在加载公告…' : `共 ${notices.items.length} 条公告` }}
        </span>
        <button class="btn btn-primary" @click="emit('close')">关闭</button>
      </div>
    </template>
  </Modal>

  <Modal :open="open && !!selected" wide :title="detail.title" @close="selectedId = null">
    <template #header>
      <div class="notice-header">
        <span class="notice-header-icon"><Icon name="info" :size="19" /></span>
        <span class="badge badge-accent plain">公告</span>
      </div>
    </template>

    <template v-if="selected">
      <h2 class="notice-detail-title">{{ detail.title }}</h2>
      <div class="notice-detail-meta">
        <span class="num">
          <Icon name="clock" :size="14" />
          {{ relative(selected.created_at) }} · {{ dateTime(selected.created_at, { seconds: true }) }}
        </span>
        <span><Icon name="eye" :size="14" />已读</span>
      </div>
      <div class="notice-detail-body">
        <template v-for="(block, i) in detail.blocks" :key="i">
          <template v-if="block.src">
            <a
              v-if="!broken.has(block.src)"
              class="notice-image"
              :href="block.src"
              target="_blank"
              rel="noopener noreferrer"
              title="查看原图"
            >
              <img :src="block.src" alt="公告图片" loading="lazy" @error="broken.add(block.src)" />
            </a>
            <a v-else :href="block.src" target="_blank" rel="noopener noreferrer">{{ block.src }}</a>
          </template>
          <p v-else>{{ block.text }}</p>
        </template>
      </div>
    </template>

    <template #footer>
      <div class="notice-footer">
        <span class="notice-footer-hint">
          <Icon name="info" :size="14" />
          您已阅读此公告
        </span>
        <button class="btn" @click="selectedId = null">返回</button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Modal from '@/components/base/Modal.vue'
import { sessionStore } from '@/stores'
import { dateTime, relative } from '@/utils/format'
import NoticeEditor from './NoticeEditor.vue'
import NoticeItem from './NoticeItem.vue'

// The bell owns this controller so read state survives closing the dialog.
const props = defineProps({
  open: Boolean,
  notices: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const IMAGE_LINE = /^https:\/\/\S+\.(?:png|jpe?g|gif|webp)(?:[?#]\S*)?$/i
const composing = ref(false)
const editingId = ref(null)
const activeItemId = ref(null)
const selectedId = ref(null)
const scroller = ref(null)
const broken = reactive(new Set())

watch(
  () => props.open,
  (open) => {
    if (!open) return
    composing.value = false
    editingId.value = null
    selectedId.value = null
  },
)

const selected = computed(() => props.notices.items.find((item) => item.id === selectedId.value) || null)

function noticeTitle(notice) {
  const first = notice.content.trim().split(/\r?\n/, 1)[0].trim()
  return IMAGE_LINE.test(first) ? '图片公告' : first
}

// A line holding only an https image link shows as that image; other lines stay text.
const detail = computed(() => {
  if (!selected.value) return { title: '', blocks: [] }
  const lines = selected.value.content.trim().split(/\r?\n/)
  const title = IMAGE_LINE.test(lines[0].trim()) ? '图片公告' : lines.shift()
  const blocks = []
  for (const line of lines) {
    const trimmed = line.trim()
    const last = blocks.at(-1)
    if (IMAGE_LINE.test(trimmed)) blocks.push({ src: trimmed })
    else if (last && !last.src) last.text += `\n${line}`
    else blocks.push({ text: line })
  }
  const filtered = blocks.filter((b) => b.src || (b.text = b.text.trim()))
  return { title, blocks: filtered.length ? filtered : [{ text: title }] }
})

function openDetail(notice) {
  props.notices.markRead(notice)
  selectedId.value = notice.id
}
function startCompose() {
  activeItemId.value = null
  editingId.value = null
  composing.value = true
}
async function publish(content) {
  const notice = await props.notices.create(content)
  if (!notice) return
  composing.value = false
  if (scroller.value) scroller.value.scrollTop = 0
}
function startEdit(id) {
  activeItemId.value = null
  composing.value = false
  editingId.value = id
}
async function saveEdit(id, content) {
  if (await props.notices.update(id, content)) editingId.value = null
}
</script>

<style scoped>
.notice-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.notice-header-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--accent);
  color: var(--on-accent);
}
.notice-header .modal-title {
  font-size: 18px;
  line-height: 1.2;
}
.notice-subtitle {
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
}
.notice-unread-num {
  color: var(--accent-text);
  font-weight: 600;
}
.notice-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.notice-compose {
  margin-bottom: 16px;
}
.notice-scroll {
  margin-right: -8px;
  padding-right: 8px;
  max-height: 56vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
}
.notice-list {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--border);
}

.notice-detail-title {
  font-size: 19px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.notice-detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  margin-top: 8px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-size: 12.5px;
}
.notice-detail-meta > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.notice-detail-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  margin-top: 16px;
  padding-left: 14px;
  border-left: 3px solid var(--accent);
  max-height: 52vh;
  overflow-y: auto;
  color: var(--text-2);
  font-size: 14px;
  line-height: 1.8;
}
.notice-detail-body p {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.notice-image {
  display: block;
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.notice-image img {
  display: block;
  max-width: 100%;
  height: auto;
}

.notice-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.notice-footer-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
}
.notice-footer > button {
  flex: none;
  min-width: 76px;
}
</style>
