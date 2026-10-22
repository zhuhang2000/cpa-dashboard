<template>
  <button type="button" class="sort-btn" :class="{ active }" @click="emit('sort', field)">
    <slot /><Icon :name="active ? (sort.desc ? 'chevron-down' : 'chevron-up') : 'chevrons-up-down'" :size="12" />
  </button>
</template>

<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

// A table header label that sorts by `field`; `sort` is the list's current { key, desc }.
const props = defineProps({
  field: { type: String, required: true },
  sort: { type: Object, required: true },
})
const emit = defineEmits(['sort'])
const active = computed(() => props.sort.key === props.field)
</script>

<style scoped>
.sort-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  color: inherit;
  cursor: pointer;
}
.sort-btn:hover,
.sort-btn.active {
  color: var(--text);
}
.sort-btn :deep(svg) {
  opacity: 0.45;
}
.sort-btn.active :deep(svg) {
  opacity: 1;
}
</style>
