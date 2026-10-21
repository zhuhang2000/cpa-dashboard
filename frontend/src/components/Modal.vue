<template>
  <Teleport to="body">
    <div v-if="open" class="modal-overlay" @mousedown.self="onBackdrop">
      <div class="modal" :class="{ wide }" role="dialog" aria-modal="true" :aria-label="title">
        <div class="modal-header">
          <slot name="header">
            <div class="modal-title">{{ title }}</div>
          </slot>
          <button class="btn btn-ghost btn-icon btn-sm" type="button" aria-label="关闭" @click="emit('close')">
            <Icon name="x" :size="18" />
          </button>
        </div>
        <div class="modal-body"><slot /></div>
        <div v-if="$slots.footer" class="modal-footer"><slot name="footer" /></div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  open: Boolean,
  title: { type: String, default: '' },
  wide: Boolean,
  persistent: Boolean,
})
const emit = defineEmits(['close'])

function onKey(e) {
  if (e.key === 'Escape' && !props.persistent) emit('close')
}
function onBackdrop() {
  if (!props.persistent) emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) document.addEventListener('keydown', onKey)
    else document.removeEventListener('keydown', onKey)
  },
  { immediate: true },
)
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>
