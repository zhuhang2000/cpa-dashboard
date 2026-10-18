<template>
  <span class="badge" :class="entry.tone ? `badge-${entry.tone}` : ''">{{ entry.label }}</span>
</template>

<script setup>
import { computed } from 'vue'

// `map` is one of the label maps in constants.js; unknown values show as-is in the neutral tone.
const props = defineProps({
  map: { type: Object, required: true },
  value: { type: String, default: '' },
})

const entry = computed(() => props.map[props.value] || { label: props.value, tone: '' })
</script>
