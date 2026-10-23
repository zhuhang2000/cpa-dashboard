<template>
  <Modal open xwide title="充值记录" @close="emit('close')">
    <div class="stack">
      <div class="records-toolbar">
        <div class="records-bar">
          <div class="records-filters">
            <SelectMenu
              v-model="range"
              :options="RANGE_OPTIONS"
              class="input-sm"
              label="时间范围"
              @change="records.load(1)"
            />
            <SelectMenu
              v-model="type"
              :options="TYPE_OPTIONS"
              class="input-sm"
              label="类型"
              @change="records.load(1)"
            />
            <SelectMenu
              v-model="tag"
              :options="tagOptions"
              class="input-sm"
              label="用户标签"
              @change="records.load(1)"
            />
            <SelectMenu
              v-model="operator"
              :options="operatorOptions"
              class="input-sm"
              label="操作人"
              @change="records.load(1)"
            />
          </div>
          <SearchInput
            v-model="q"
            placeholder="搜索用户名或邮箱，回车确认"
            label="搜索用户"
            @search="records.load(1)"
          />
        </div>
        <div v-if="range === 'custom'" class="records-filters">
          <input
            v-model="customStart"
            class="input input-sm"
            type="date"
            aria-label="开始日期"
            @change="records.load(1)"
          />
          <span class="muted">至</span>
          <input
            v-model="customEnd"
            class="input input-sm"
            type="date"
            aria-label="结束日期"
            @change="records.load(1)"
          />
        </div>
      </div>
      <div class="card">
        <div class="summary-bar">
          <span
            ><b class="num">{{ num(records.total) }}</b> 条记录</span
          >
          <span
            >增加 <b class="num text-success">{{ money(records.sum_credit, { sign: true }) }}</b></span
          >
          <span
            >扣减 <b class="num text-danger">{{ money(records.sum_debit) }}</b></span
          >
          <span
            >合计 <b class="num">{{ money(records.sum_amount, { sign: true }) }}</b></span
          >
        </div>
        <TransactionTable :list="records" with-user />
      </div>
    </div>
    <template #footer>
      <button type="button" class="btn" @click="emit('close')">关闭</button>
    </template>
  </Modal>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Modal from '@/components/base/Modal.vue'
import SearchInput from '@/components/base/SearchInput.vue'
import SelectMenu from '@/components/base/SelectMenu.vue'
import TransactionTable from '@/components/shared/TransactionTable.vue'
import { accountsApi } from '@/api/accounts'
import { billingApi } from '@/api/billing'
import { usePagedList } from '@/composables/usePagedList'
import { ROLES, TX_TYPES } from '@/constants'
import { money, num, rangeBounds, toInputDate } from '@/utils/format'

// Presets understood by rangeBounds.
const RANGE_OPTIONS = [
  { value: 'today', label: '今天' },
  { value: '7d', label: '近 7 天' },
  { value: 'month', label: '本月' },
  { value: 'last_month', label: '上月' },
  { value: 'all', label: '全部时间' },
  { value: 'custom', label: '自定义' },
]
const TYPE_OPTIONS = [
  { value: '', label: '全部类型' },
  ...Object.entries(TX_TYPES).map(([value, entry]) => ({ value, label: entry.label })),
]

// Every user's ledger: redeem codes, online payments, and administrators' adjustments and gifts.
// The tag filter keeps the users carrying the tag now, each with its whole history.
const emit = defineEmits(['close'])
const range = ref('month')
// A custom range starts as this month so far.
const customStart = ref(toInputDate(rangeBounds('month').start))
const customEnd = ref(toInputDate(Date.now()))
const q = ref('')
const type = ref('')
const tag = ref('')
const operator = ref('')
const tags = ref([])
// Every filter, the date range included, narrows both the page and the totals the API returns.
const records = usePagedList(
  billingApi.adminListAllTransactions,
  () => ({
    ...rangeBounds(range.value, customStart.value, customEnd.value),
    q: q.value,
    type: type.value,
    tag: tag.value,
    operator: operator.value,
  }),
  { sum_amount: 0, sum_credit: 0, sum_debit: 0, operators: [] },
)
const tagOptions = computed(() => [
  { value: '', label: '全部标签' },
  ...tags.value.map((t) => ({ value: t.tag, label: t.tag })),
])
const operatorOptions = computed(() => [
  { value: '', label: '全部操作人' },
  ...records.operators.map((o) => ({
    value: String(o.id),
    label: `${o.username}（${ROLES[o.role]?.label || o.role}）`,
  })),
])

onMounted(async () => {
  records.load(1)
  // A failed load only leaves the tag filter at "all".
  try {
    tags.value = (await accountsApi.adminListTags()).items
  } catch {
    tags.value = []
  }
})
</script>

<style scoped>
/* One row of dropdowns with the user search at its end; a custom range adds its dates below. */
.records-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.records-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.records-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
/* SelectMenu renders its .select trigger itself, hence :deep. */
.records-filters .input,
.records-filters :deep(.select) {
  width: auto;
  min-width: 120px;
}
</style>
