<template>
  <div v-if="tier.label" class="tabs">
    <button type="button" class="tab" :class="{ active: !tier.long }" @click="tier.show(false)">标准价格</button>
    <button type="button" class="tab" :class="{ active: tier.long }" @click="tier.show(true)">{{ tier.label }}</button>
  </div>
</template>

<script>
import { computed, reactive } from 'vue'

// 272000 → 272K, 1000000 → 1M.
function size(n) {
  return n >= 1e6 ? `${n / 1e6}M` : `${n / 1e3}K`
}

// Which prices the user and admin price pages show: the standard ones, or the long-context tier
// a request is billed at once its input (cache included) exceeds the threshold. `prices` returns
// the price objects of the page (each with `tiers`); a model without a tier, such as an
// administrator override, costs the same at any length.
export function usePriceTiers(prices) {
  const thresholds = computed(() => [...new Set(prices().flatMap((p) => (p?.tiers ?? []).map((t) => t.threshold)))])
  const tier = reactive({
    long: false,
    // Empty when no model has a tier, which hides the switch.
    label: computed(() => {
      // first：取得数组的第 1 个元素（即 thresholds.value[0]）。...rest：把剩下的所有元素收集为一个新的子数组（即 thresholds.value.slice(1)）。
      const [first, ...rest] = thresholds.value
      if (first === undefined) return ''
      return rest.length ? '长上下文' : `超过 ${size(first)}`
    }),
    show(long) {
      tier.long = long
    },
    rates(price) {
      return (tier.long && price?.tiers?.[0]) || price
    },
    // The line under a model's name while long-context prices are shown.
    note(price) {
      if (!tier.long || !price) return ''
      if (!price.tiers?.length) return '不区分上下文长度'
      return thresholds.value.length > 1 ? `超过 ${size(price.tiers[0].threshold)} 时` : ''
    },
  })
  return tier
}
</script>

<script setup>
// The standard / long-context switch of the price pages; `tier` comes from usePriceTiers().
defineProps({ tier: { type: Object, required: true } })
</script>
