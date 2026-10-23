<template>
  <button
    ref="trigger"
    v-bind="$attrs"
    type="button"
    class="select select-menu"
    :class="{ placeholder: !selected }"
    role="combobox"
    aria-haspopup="listbox"
    :aria-expanded="list.open"
    :aria-controls="list.open ? listId : undefined"
    :aria-activedescendant="list.open && active >= 0 ? `${listId}-${active}` : undefined"
    :aria-label="label || undefined"
    @click="toggle"
    @keydown="onKeydown"
  >
    {{ selected ? selected.label : placeholder }}
  </button>
  <Teleport to="body">
    <div
      v-if="list.open"
      :id="listId"
      ref="panel"
      class="dropdown-menu floating"
      :style="list.style"
      role="listbox"
      :aria-label="label || undefined"
      @mousedown.prevent
    >
      <button
        v-for="(option, index) in options"
        :id="`${listId}-${index}`"
        :key="option.value"
        type="button"
        class="dropdown-item"
        :class="{ active: index === active }"
        role="option"
        :aria-selected="option.value === value"
        tabindex="-1"
        @click="pick(option)"
      >
        {{ option.label }}
        <Icon name="check" :size="15" class="dropdown-check" />
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, useId } from 'vue'
import Icon from './Icon.vue'
import { usePopover } from '@/composables/usePopover'

// A select whose list looks like the app's dropdown menus rather than the browser's own. `options`
// are { value, label }; `placeholder` shows while the value matches none of them; `change` follows a
// pick that changed the value. id, class and the like go on the trigger, a button styled as a
// .select (add input-sm for the small size), so a <label for> names it.
defineOptions({ inheritAttrs: false })
const props = defineProps({
  options: { type: Array, required: true },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})
const value = defineModel({ type: String, default: '' })
const emit = defineEmits(['change'])

const listId = useId()
const trigger = ref(null)
const panel = ref(null)
const active = ref(-1) // the option highlighted with the arrow keys
// The list is teleported out of any dialog, whose body scrolls, and placed under the trigger.
const list = usePopover({
  panel,
  place: (rect) => ({
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    minWidth: `${rect.width}px`,
    maxHeight: `${Math.max(120, innerHeight - rect.bottom - 16)}px`,
  }),
})
const selected = computed(() => props.options.find((option) => option.value === value.value))

function highlight(index) {
  active.value = index
  nextTick(() => document.getElementById(`${listId}-${index}`)?.scrollIntoView({ block: 'nearest' }))
}

// Opening starts from the chosen option, as a native select does.
function toggle(event) {
  list.toggle(event)
  if (list.open) highlight(props.options.indexOf(selected.value))
}

function pick(option) {
  list.close()
  if (option.value === value.value) return
  value.value = option.value
  emit('change', option.value)
}

function onKeydown(e) {
  if (e.key === 'Tab') return list.close()
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    if (!list.open) {
      list.show(trigger.value)
      return highlight(props.options.indexOf(selected.value))
    }
    const next = active.value + (e.key === 'ArrowDown' ? 1 : -1)
    highlight(next < 0 ? props.options.length - 1 : next % props.options.length)
  } else if (e.key === 'Enter' && list.open && active.value >= 0) {
    // Pick the highlighted option instead of letting the click close the list.
    e.preventDefault()
    pick(props.options[active.value])
  }
}
</script>

<style scoped>
/* .select draws the border and arrow; a button also needs its label kept on one line. */
.select-menu {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
  cursor: pointer;
}
/* Same as an empty .input's placeholder. */
.select-menu.placeholder {
  color: var(--faint);
}
</style>
