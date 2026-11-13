<template>
  <li class="notice-item" :class="{ unread }">
    <NoticeEditor
      v-if="editing"
      :value="notice.content"
      label="编辑公告"
      :saving="saving"
      @submit="emit('save', $event)"
      @cancel="emit('cancel-edit')"
    />
    <template v-else>
      <div
        class="notice-item-row"
        role="button"
        tabindex="0"
        @click="emit('select')"
        @keydown.enter.prevent="emit('select')"
        @keydown.space.prevent="emit('select')"
      >
        <span class="notice-item-icon" aria-hidden="true">
          <Icon :name="unread ? 'info' : 'check-circle'" :size="19" />
        </span>
        <div class="notice-item-body">
          <h3 class="notice-title">{{ title }}</h3>
          <div class="notice-meta">
            <span class="num">{{ relative(notice.created_at) }}</span>
            <span v-if="unread" class="badge badge-accent">未读</span>
          </div>
        </div>
        <button
          v-if="isAdmin"
          type="button"
          class="btn btn-ghost btn-icon btn-sm notice-more"
          :aria-label="`更多操作：${title}`"
          :aria-expanded="actions.open"
          :aria-controls="actions.open ? menuId : undefined"
          title="更多操作"
          @click.stop="toggleActions"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <circle cx="5" cy="12" r="1.7" />
            <circle cx="12" cy="12" r="1.7" />
            <circle cx="19" cy="12" r="1.7" />
          </svg>
        </button>
        <Icon name="chevron-right" :size="17" class="notice-arrow" />
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
import { nextTick, ref, useId, watch } from 'vue'
import Icon from '@/components/base/Icon.vue'
import { usePopover } from '@/composables/usePopover'
import { relative } from '@/utils/format'
import NoticeEditor from './NoticeEditor.vue'

const props = defineProps({
  notice: { type: Object, required: true },
  title: { type: String, required: true },
  unread: Boolean,
  isAdmin: Boolean,
  saving: Boolean,
  editing: Boolean,
  active: Boolean,
})
const emit = defineEmits(['select', 'activate', 'edit', 'save', 'cancel-edit', 'remove'])
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
  position: relative;
  padding: 14px 12px;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}
.notice-item:last-child {
  border-bottom-color: transparent;
}
.notice-item.unread::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 999px;
  background: var(--accent);
}
.notice-item-row {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
}
.notice-item:hover {
  background: var(--surface-2);
}
.notice-item-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--surface-3);
  color: var(--faint);
}
.notice-item.unread .notice-item-icon {
  background: var(--accent);
  color: var(--on-accent);
}
.notice-item-body {
  flex: 1;
  min-width: 0;
}
.notice-title {
  font-size: 14.5px;
  font-weight: 500;
  line-height: 1.45;
  color: var(--text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.notice-item.unread .notice-title {
  font-weight: 600;
  color: var(--text);
}
.notice-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
.notice-more {
  flex: none;
  color: var(--muted);
}
.notice-more[aria-expanded='true'] {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.notice-arrow {
  flex: none;
  color: var(--faint);
}
.notice-confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-left: 52px;
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
    padding: 12px 8px;
  }
  .notice-confirm {
    padding-left: 0;
  }
}
</style>
