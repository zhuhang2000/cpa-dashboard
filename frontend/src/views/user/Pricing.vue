<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">模型价格</h1>
        <p class="page-desc">按实际消耗的 tokens 计费，失败的请求不收费。</p>
      </div>
      <div class="page-actions">
        <div class="tabs">
          <button class="tab" :class="{ active: unit === 'M' }" @click="unit = 'M'">每百万 tokens</button>
          <button class="tab" :class="{ active: unit === 'K' }" @click="unit = 'K'">每千 tokens</button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <SearchInput v-model="q" placeholder="搜索模型" />
        <span class="muted">{{ filtered.length }} 个模型</span>
      </div>
      <div v-if="loading" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState
        v-else-if="!filtered.length"
        icon="tag"
        :title="q ? '没有匹配的模型' : '暂无模型价格'"
        :desc="q ? '' : '管理员配置价格后会显示在这里'"
      />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>模型</th>
              <th class="right">输入</th>
              <th class="right">输出</th>
              <th class="right">缓存读取</th>
              <th class="right">缓存写入</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in filtered" :key="m.model">
              <td>
                <div class="row" style="gap: 10px">
                  <ModelLogo :model="m.model" />
                  <div>
                    <div class="row" style="gap: 4px">
                      <span class="mono cell-main">{{ m.model }}</span>
                      <CopyButton :text="m.model" />
                    </div>
                    <div v-if="m.note" class="cell-sub">{{ m.note }}</div>
                  </div>
                </div>
              </td>
              <td v-for="part in ['input', 'output']" :key="part" class="right num nowrap">
                <div v-if="saved && m.official" class="deal">
                  <s class="was" title="官方价">{{ show(m.official[part]) }}</s>
                  <span class="badge badge-accent plain save">省 {{ saved }}%</span>
                </div>
                <div class="now">{{ show(m[part]) }}</div>
              </td>
              <td class="right num muted">{{ show(m.cache_read) }}</td>
              <td class="right num muted">{{ show(m.cache_write) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="card-footer muted" style="font-size: 12.5px">
        <span
          >费用 = 输入 tokens × 输入单价 + 输出 tokens × 输出单价（命中缓存的输入按缓存价格计算），推理 tokens
          计入输出。<template v-if="saved">划线价为官方价，缓存价格同样打折。</template></span
        >
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import CopyButton from '@/components/base/CopyButton.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import SearchInput from '@/components/base/SearchInput.vue'
import ModelLogo from '@/components/shared/ModelLogo.vue'
import { pricingApi } from '@/api/pricing'
import { price } from '@/utils/format'
import { toast } from '@/toast'

const items = ref([])
const discount = ref(1)
const loading = ref(true)
const q = ref('')
const unit = ref('M')

const filtered = computed(() => {
  const term = q.value.toLowerCase()
  return term ? items.value.filter((m) => m.model.toLowerCase().includes(term)) : items.value
})
// Percent of the official price the discount saves (0.8 → 20); 0 when there is no discount.
const saved = computed(() => Number(((1 - discount.value) * 100).toFixed(1)))

function show(v) {
  if (v === null || v === undefined) return '—'
  return price(unit.value === 'K' ? v / 1000 : v)
}

onMounted(async () => {
  try {
    const data = await pricingApi.listPrices()
    items.value = data.items
    discount.value = data.discount
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* A discounted price: the struck official price and the saving above the price paid. */
.deal {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}
/* The rule is drawn at the middle of the box because line-through sits at half the
   x-height, low across digits. */
.was {
  position: relative;
  color: var(--muted);
  font-size: 12px;
  text-decoration: none;
}
.was::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  border-top: 1px solid;
}
.save {
  height: 20px;
  padding: 0 7px;
  font-size: 11.5px;
  font-weight: 600;
}
.now {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
</style>
