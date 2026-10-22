<template>
  <form class="input-group has-prefix search-input" @submit.prevent="emit('search')">
    <span class="input-prefix"><Icon name="search" :size="15" /></span>
    <input v-model.trim="query" class="input input-sm" :placeholder="placeholder" :aria-label="label || placeholder" />
  </form>
</template>

<script setup>
import Icon from './Icon.vue'

// v-model filters as you type; pages that search on the server listen for `search` (Enter).
defineProps({
  placeholder: { type: String, default: '搜索' },
  label: { type: String, default: '' },
})
const query = defineModel({ type: String, default: '' })
const emit = defineEmits(['search'])
</script>

<style scoped>
.search-input {
  width: 260px;
  max-width: 100%;
}
/* Wider than the default prefix padding, for the search icon. */
.search-input .input {
  padding-left: 32px;
}
</style>
