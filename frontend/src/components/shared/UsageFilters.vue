<template>
  <div class="card-body usage-filters">
    <div class="tabs">
      <button
        v-for="p in PRESETS"
        :key="p.key"
        type="button"
        class="tab"
        :class="{ active: filters.range === p.key }"
        @click="set({ range: p.key })"
      >
        {{ p.label }}
      </button>
    </div>
    <template v-if="filters.range === 'custom'">
      <input
        :value="filters.from"
        class="input input-sm"
        type="date"
        aria-label="开始日期"
        @change="set({ from: $event.target.value })"
      />
      <span class="muted">至</span>
      <input
        :value="filters.to"
        class="input input-sm"
        type="date"
        aria-label="结束日期"
        @change="set({ to: $event.target.value })"
      />
    </template>
    <select
      :value="filters.keyId"
      class="select input-sm"
      aria-label="密钥"
      @change="set({ keyId: $event.target.value })"
    >
      <option value="">全部密钥</option>
      <option v-for="k in keys" :key="k.id" :value="String(k.id)">{{ k.name }}</option>
    </select>
    <select
      :value="filters.model"
      class="select input-sm"
      aria-label="模型"
      @change="set({ model: $event.target.value })"
    >
      <option value="">全部模型</option>
      <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
    </select>
    <select
      :value="filters.status"
      class="select input-sm"
      aria-label="状态"
      @change="set({ status: $event.target.value })"
    >
      <option value="">全部状态</option>
      <option value="success">成功</option>
      <option value="failed">失败</option>
    </select>
  </div>
</template>

<script>
import { rangeBounds, toInputDate } from '@/utils/format'

export function usageFilters(range = '7d') {
  return {
    range,
    from: toInputDate(Date.now() - 6 * 86400000),
    to: toInputDate(Date.now()),
    keyId: '',
    model: '',
    status: '',
  }
}

export function usageQuery(f) {
  return { ...rangeBounds(f.range, f.from, f.to), key_id: f.keyId, model: f.model, status: f.status }
}
</script>

<script setup>
const PRESETS = [
  { key: 'today', label: '今天' },
  { key: '7d', label: '近 7 天' },
  { key: '30d', label: '近 30 天' },
  { key: 'all', label: '全部' },
  { key: 'custom', label: '自定义' },
]

const filters = defineModel({ type: Object, required: true })
defineProps({
  keys: { type: Array, default: () => [] },
  models: { type: Array, default: () => [] },
})
const emit = defineEmits(['change'])

function set(patch) {
  filters.value = { ...filters.value, ...patch }
  emit('change')
}
</script>

<style scoped>
.usage-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding-bottom: 14px;
}
.usage-filters .input,
.usage-filters .select {
  width: auto;
  min-width: 140px;
}
</style>
