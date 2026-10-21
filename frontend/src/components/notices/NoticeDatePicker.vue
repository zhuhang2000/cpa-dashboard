<template>
  <button
    v-if="selectedDay"
    ref="pickerBtn"
    class="notice-picker-btn"
    aria-haspopup="listbox"
    :aria-expanded="open"
    :aria-controls="open ? menuId : undefined"
    @click="toggle"
  >
    {{ selectedDay.displayDate }}
    <span class="notice-count">{{ selectedDay.items.length }} 条</span>
    <Icon name="chevron-down" :size="16" class="notice-picker-arrow" />
  </button>
  <Teleport to="body">
    <div
      v-if="open"
      :id="menuId"
      ref="pickerMenu"
      class="notice-picker-menu"
      :style="pickerStyle"
      role="listbox"
      aria-label="公告日期"
    >
      <button
        v-for="day in days"
        :key="day.key"
        class="notice-picker-option"
        :class="{ active: day.key === selectedDay?.key }"
        role="option"
        :aria-selected="day.key === selectedDay?.key"
        @click="pickDay(day.key)"
      >
        <span class="notice-picker-day">{{ day.label }}</span>
        <span class="notice-picker-week">{{ day.caption }}</span>
        <span class="notice-count">{{ day.items.length }} 条</span>
        <Icon name="check" :size="15" class="notice-picker-check" />
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, useId, watch } from 'vue'
import Icon from '@/components/Icon.vue'

const props = defineProps({ days: { type: Array, required: true } })
const selectedKey = defineModel({ type: String, default: '' })
const emit = defineEmits(['open'])
const open = ref(false)
const menuId = useId()
const pickerBtn = ref(null)
const pickerMenu = ref(null)
const pickerStyle = ref({})
const selectedDay = computed(() => props.days.find((day) => day.key === selectedKey.value) || props.days[0])

function close() {
  open.value = false
}
function toggle() {
  if (open.value) return close()
  emit('open')
  const rect = pickerBtn.value.getBoundingClientRect()
  const width = Math.min(Math.max(rect.width, 280), innerWidth - 32)
  pickerStyle.value = {
    top: `${rect.bottom + 6}px`,
    left: `${Math.max(16, Math.min(rect.left, innerWidth - width - 16))}px`,
    width: `${width}px`,
    maxHeight: `${Math.max(160, innerHeight - rect.bottom - 24)}px`,
  }
  open.value = true
}
function pickDay(key) {
  selectedKey.value = key
  close()
  pickerBtn.value?.focus()
}
function onPointerDown(e) {
  if (!pickerBtn.value?.contains(e.target) && !pickerMenu.value?.contains(e.target)) close()
}
function onKey(e) {
  if (e.key !== 'Escape') return
  e.preventDefault()
  e.stopImmediatePropagation()
  close()
  pickerBtn.value?.focus()
}
function onScroll(e) {
  if (!pickerMenu.value?.contains(e.target)) close()
}
watch(open, (isOpen, _, onCleanup) => {
  if (!isOpen) return
  document.addEventListener('pointerdown', onPointerDown)
  document.addEventListener('keydown', onKey, true)
  document.addEventListener('scroll', onScroll, true)
  window.addEventListener('resize', close)
  onCleanup(() => {
    document.removeEventListener('pointerdown', onPointerDown)
    document.removeEventListener('keydown', onKey, true)
    document.removeEventListener('scroll', onScroll, true)
    window.removeEventListener('resize', close)
  })
})

defineExpose({ close })
</script>

<style scoped>
.notice-count {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 12px;
  font-weight: 600;
}

.notice-picker-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  cursor: pointer;
}
.notice-picker-btn:hover,
.notice-picker-btn[aria-expanded='true'] {
  border-color: var(--accent);
}
.notice-picker-arrow {
  color: var(--muted);
  transition: transform 0.15s;
}
.notice-picker-btn[aria-expanded='true'] .notice-picker-arrow {
  transform: rotate(180deg);
}
.notice-picker-menu {
  position: fixed;
  z-index: 110;
  padding: 6px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  box-shadow: var(--shadow-lg);
}
.notice-picker-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 40px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-2);
  text-align: left;
  cursor: pointer;
}
.notice-picker-option:hover {
  background: var(--surface-3);
}
.notice-picker-option.active {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.notice-picker-day {
  font-weight: 600;
}
.notice-picker-week {
  flex: 1;
  font-size: 12.5px;
  color: var(--muted);
}
.notice-picker-option:not(.active) .notice-count {
  background: var(--surface-3);
  color: var(--muted);
}
.notice-picker-check {
  visibility: hidden;
}
.notice-picker-option.active .notice-picker-check {
  visibility: visible;
}
</style>
