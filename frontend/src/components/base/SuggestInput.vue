<template>
  <div ref="field" class="input-group">
    <input
      ref="input"
      v-model="value"
      v-bind="$attrs"
      class="input"
      role="combobox"
      autocomplete="off"
      aria-autocomplete="list"
      :aria-expanded="expanded"
      :aria-controls="expanded ? listId : undefined"
      :aria-activedescendant="expanded && active >= 0 ? `${listId}-${active}` : undefined"
      @click="open(false)"
      @input="open(true)"
      @keydown="onKeydown"
    />
    <button
      v-if="options.length"
      type="button"
      class="input-addon"
      tabindex="-1"
      :aria-label="expanded ? '收起选项' : '展开选项'"
      @mousedown.prevent
      @click="toggleAll"
    >
      <Icon name="chevron-down" :size="16" class="suggest-arrow" :class="{ open: expanded }" />
    </button>
  </div>
  <Teleport to="body">
    <div
      v-if="expanded"
      :id="listId"
      ref="panel"
      class="dropdown-menu suggest-menu"
      :style="list.style"
      role="listbox"
      @mousedown.prevent
    >
      <button
        v-for="(option, index) in shown"
        :id="`${listId}-${index}`"
        :key="option.value"
        type="button"
        class="dropdown-item suggest-option"
        :class="{ active: index === active }"
        role="option"
        :aria-selected="option.value === value"
        tabindex="-1"
        @click="pick(option)"
      >
        <span class="suggest-value">{{ option.value }}</span>
        <span v-if="option.hint" class="suggest-hint">{{ option.hint }}</span>
        <Icon name="check" :size="15" class="suggest-check" />
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue'
import Icon from './Icon.vue'
import { usePopover } from '@/composables/usePopover'

// A text input that suggests `options` ({ value, hint }) in a list below it. Typed text that matches
// no option is kept, so new values can be entered. id, maxlength, placeholder, required and the like
// belong on the <input>, not the wrapper.
defineOptions({ inheritAttrs: false })
const props = defineProps({ options: { type: Array, default: () => [] } })
const value = defineModel({ type: String, default: '' })

const listId = useId()
const field = ref(null)
const input = ref(null)
const panel = ref(null)
const filtering = ref(false) // narrow the list to the typed text, once the user types
const active = ref(-1) // the option highlighted with the arrow keys
// The list is teleported out of the dialog, whose body scrolls, and placed under the input.
const list = usePopover({
  panel,
  place: (rect) => ({
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    maxHeight: `${Math.max(120, innerHeight - rect.bottom - 16)}px`,
  }),
})

const shown = computed(() => {
  const text = value.value.trim().toLowerCase()
  if (!filtering.value || !text) return props.options
  return props.options.filter((option) => option.value.toLowerCase().includes(text))
})
const expanded = computed(() => list.open && shown.value.length > 0)

// An empty list closes, so an invisible popup never swallows the Escape meant for the dialog.
watch(shown, (items) => {
  active.value = -1
  if (!items.length) list.close()
})

// Opening by click or arrow key lists every option; typing narrows the list to the text. A click
// inside an open list leaves it as it is.
function open(filter) {
  if (list.open && !filter) return
  filtering.value = filter
  if (!list.open && shown.value.length) list.show(field.value)
}

function toggleAll() {
  if (list.open) return list.close()
  input.value.focus()
  open(false)
}

function pick(option) {
  value.value = option.value
  filtering.value = false
  list.close()
}

function onKeydown(e) {
  if (e.key === 'Tab') return list.close()
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    if (!expanded.value) return open(false)
    const next = active.value + (e.key === 'ArrowDown' ? 1 : -1)
    active.value = next < 0 ? shown.value.length - 1 : next % shown.value.length
    nextTick(() => document.getElementById(`${listId}-${active.value}`)?.scrollIntoView({ block: 'nearest' }))
  } else if (e.key === 'Enter' && expanded.value && active.value >= 0) {
    // Pick the highlighted option instead of submitting the form.
    e.preventDefault()
    pick(shown.value[active.value])
  }
}
</script>

<style scoped>
.suggest-arrow {
  transition: transform 0.15s;
}
.suggest-arrow.open {
  transform: rotate(180deg);
}
/* .dropdown-menu, placed by usePopover instead of under a relative parent, above .modal-overlay. */
.suggest-menu {
  position: fixed;
  right: auto;
  z-index: 110;
  overflow-y: auto;
}
.suggest-option.active {
  background: var(--surface-3);
  color: var(--text);
}
.suggest-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
  font-weight: 500;
}
.suggest-hint {
  font-size: 12px;
  color: var(--muted);
}
.suggest-check {
  flex: none;
  color: var(--accent);
  visibility: hidden;
}
.suggest-option[aria-selected='true'] .suggest-check {
  visibility: visible;
}
</style>
