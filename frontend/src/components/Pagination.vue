<template>
  <div class="row-between wrap" style="width: 100%">
    <span class="muted">共 {{ total.toLocaleString('zh-CN') }} 条</span>
    <div v-if="pages > 1" class="pagination">
      <button class="page-btn" :disabled="page <= 1" aria-label="上一页" @click="go(page - 1)">
        <Icon name="chevron-left" :size="16" />
      </button>
      <template v-for="(p, i) in items" :key="i">
        <span v-if="p === '…'" class="faint" style="padding: 0 4px">…</span>
        <button v-else class="page-btn" :class="{ active: p === page }" @click="go(p)">{{ p }}</button>
      </template>
      <button class="page-btn" :disabled="page >= pages" aria-label="下一页" @click="go(page + 1)">
        <Icon name="chevron-right" :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  page: { type: Number, required: true },
  total: { type: Number, required: true },
  pageSize: { type: Number, default: 20 },
})
const emit = defineEmits(['change'])

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const items = computed(() => {
  const n = pages.value
  const p = props.page
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1)
  const out = [1]
  const start = Math.max(2, p - 1)
  const end = Math.min(n - 1, p + 1)
  if (start > 2) out.push('…')
  for (let i = start; i <= end; i++) out.push(i)
  if (end < n - 1) out.push('…')
  out.push(n)
  return out
})

function go(p) {
  if (p >= 1 && p <= pages.value && p !== props.page) emit('change', p)
}
</script>
