<template>
  <div class="card stat">
    <div class="stat-label">
      <span class="stat-icon" :class="tone"><Icon :name="icon" :size="16" /></span>
      {{ label }}
    </div>
    <div v-if="loading" class="skeleton" style="height: 32px; width: 60%" />
    <div v-else class="stat-value" :class="valueClass">{{ value }}</div>
    <div class="stat-sub">
      <slot name="sub">{{ sub }}</slot>
    </div>
    <div v-if="$slots.action" class="stat-action"><slot name="action" /></div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({
  label: String,
  value: [String, Number],
  sub: { type: String, default: '' },
  icon: { type: String, default: 'chart' },
  tone: { type: String, default: '' },
  valueClass: { type: String, default: '' },
  loading: Boolean,
})
</script>
