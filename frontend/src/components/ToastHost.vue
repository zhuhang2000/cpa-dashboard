<template>
  <div class="toast-host" aria-live="polite">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
      <Icon :name="icons[t.type]" :size="18" />
      <span>{{ t.message }}</span>
    </div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'
import { toasts } from '@/toast'

const icons = { success: 'check-circle', error: 'x-circle', info: 'info' }
</script>
