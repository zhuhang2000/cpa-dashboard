<template>
  <li class="notice-item" :class="{ unread }">
    <NoticeEditor
      v-if="editing"
      v-model="draft"
      label="编辑公告"
      :saving="saving"
      @submit="emit('save', $event)"
      @cancel="emit('cancel-edit')"
    />
    <template v-else>
      <div class="notice-item-head">
        <h3 class="notice-title">{{ content.title }}</h3>
        <span v-if="unread" class="notice-new-tag">未读</span>
        <button
          v-if="isAdmin"
          class="btn btn-ghost btn-icon btn-sm notice-more"
          :aria-label="`更多操作：${content.title}`"
          :aria-expanded="actions.open"
          :aria-controls="actions.open ? menuId : undefined"
          title="更多操作"
          @click="toggleActions"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <circle cx="5" cy="12" r="1.7" />
            <circle cx="12" cy="12" r="1.7" />
            <circle cx="19" cy="12" r="1.7" />
          </svg>
        </button>
      </div>
      <p v-if="content.body" class="notice-body">{{ content.body }}</p>
      <div class="notice-meta">
        <span class="num">{{ dateTime(notice.created_at).slice(11) }}</span>
        <span aria-hidden="true">·</span>
        <span>平台公告</span>
        <span v-if="notice.updated_at > notice.created_at">· 已编辑</span>
      </div>
      <div v-if="confirming" class="notice-confirm" role="group" aria-label="确认删除公告">
        <span>确定删除这条公告？</span>
        <button class="btn btn-sm" :disabled="saving" @click="confirming = false">取消</button>
        <button class="btn btn-sm notice-danger" :disabled="saving" @click="emit('remove')">删除</button>
      </div>
    </template>
    <Teleport to="body">
      <div
        v-if="actions.open"
        :id="menuId"
        ref="actionMenu"
        class="notice-action-menu"
        :style="actions.style"
        role="group"
        aria-label="公告操作"
      >
        <button @click="startEdit"><Icon name="pencil" :size="15" />编辑公告</button>
        <button class="notice-danger" @click="confirmRemove"><Icon name="trash" :size="15" />删除公告</button>
      </div>
    </Teleport>
  </li>
</template>

<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue'
import Icon from '@/components/base/Icon.vue'
import { usePopover } from '@/composables/usePopover'
import { dateTime } from '@/utils/format'
import NoticeEditor from './NoticeEditor.vue'

const props = defineProps({
  notice: { type: Object, required: true },
  unread: Boolean,
  isAdmin: Boolean,
  saving: Boolean,
  editing: Boolean,
  active: Boolean,
})
const emit = defineEmits(['activate', 'edit', 'save', 'cancel-edit', 'remove'])
const draft = ref('')
const confirming = ref(false)
const menuId = useId()
const actionMenu = ref(null)
const actions = usePopover({
  panel: actionMenu,
  place: (rect) => ({
    left: `${Math.max(16, Math.min(rect.right - 148, innerWidth - 164))}px`,
    top: `${rect.bottom + 100 > innerHeight ? rect.top - 94 : rect.bottom + 6}px`,
  }),
})
const content = computed(() => {
  const [title, ...body] = props.notice.content.trim().split(/\r?\n/)
  return { title, body: body.join('\n').trim() }
})

watch(
  () => props.editing,
  (editing) => {
    if (editing) draft.value = props.notice.content
  },
  { immediate: true },
)
watch(
  () => props.active,
  (active) => {
    if (!active) {
      actions.close()
      confirming.value = false
    }
  },
)

async function toggleActions(event) {
  if (!actions.open) {
    emit('activate')
    confirming.value = false
  }
  actions.toggle(event)
  if (!actions.open) return
  await nextTick()
  actionMenu.value?.querySelector('button')?.focus()
}
function startEdit() {
  actions.close()
  emit('edit')
}
function confirmRemove() {
  confirming.value = true
  actions.close({ focus: true })
}
</script>

<style scoped>
.notice-item {
  padding: 18px 14px;
  border-bottom: 1px solid var(--border);
}
.notice-item:last-child {
  border-bottom-color: transparent;
}
.notice-item.unread {
  border-radius: 10px;
  border-bottom-color: transparent;
  background: color-mix(in srgb, var(--accent-soft) 55%, var(--surface));
}
.notice-item-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.notice-title {
  min-width: 0;
  font-size: 15px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.notice-new-tag {
  flex: none;
  margin-top: 3px;
  color: var(--accent-text);
  font-size: 11px;
  font-weight: 500;
}
.notice-more {
  flex: none;
  margin: -2px -4px -2px auto;
  color: var(--muted);
}
.notice-more[aria-expanded='true'] {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.notice-body {
  margin-top: 6px;
  color: var(--text-2);
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.notice-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}
.notice-confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  font-size: 13px;
}
.notice-confirm > span {
  flex: 1;
}
.notice-danger {
  color: var(--danger);
}
.notice-action-menu {
  position: fixed;
  z-index: 110;
  width: 148px;
  padding: 5px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  box-shadow: var(--shadow-lg);
}
.notice-action-menu button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-2);
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}
.notice-action-menu button:hover {
  background: var(--surface-3);
}
.notice-action-menu .notice-danger {
  color: var(--danger);
}

@media (max-width: 480px) {
  .notice-item {
    padding: 16px 10px;
  }
}
</style>
