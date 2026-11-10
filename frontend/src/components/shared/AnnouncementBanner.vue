<template>
  <div class="announcement" :style="{ width: `${width || DEFAULT_WIDTH}px` }">
    <img :src="url" alt="公告" @load="emit('load', $event)" @error="emit('error')" />
    <button v-if="closable" class="announcement-close" aria-label="关闭公告" @click="emit('close')">
      <Icon name="x" :size="14" />
    </button>
  </div>
</template>

<script>
// The admin's promo picture, on the user's overview and as the settings preview, so both look the same.
// Width used until the admin sets one; the height always follows the picture's proportions.
export const DEFAULT_WIDTH = 480
</script>

<script setup>
import Icon from '@/components/base/Icon.vue'

defineProps({
  url: { type: String, required: true },
  width: { type: Number, default: 0 },
  closable: Boolean,
})
const emit = defineEmits(['close', 'load', 'error'])
</script>

<style scoped>
/* The set width, scaled down in proportion where the space is narrower (phones, the settings card). */
.announcement {
  position: relative;
  max-width: 100%;
}
.announcement img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: var(--radius);
}
.announcement-close {
  position: absolute;
  top: 8px;
  right: 8px;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.35);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s;
}
.announcement-close:hover {
  background: rgba(0, 0, 0, 0.55);
}
</style>
