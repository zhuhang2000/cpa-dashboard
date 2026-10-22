<template>
  <div class="empty">
    <div class="empty-icon"><Icon :name="icon" :size="22" /></div>
    <div class="empty-title">{{ title }}</div>
    <div v-if="desc">{{ desc }}</div>
    <div v-if="$slots.default" style="margin-top: 8px"><slot /></div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({
  title: { type: String, default: '暂无数据' },
  desc: { type: String, default: '' },
  icon: { type: String, default: 'box' },
})
</script>
