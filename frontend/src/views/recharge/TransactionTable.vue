<template>
  <div v-if="list.loading && !list.items.length" class="card-body stack" style="gap: 10px">
    <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
  </div>
  <EmptyState v-else-if="!list.items.length" icon="receipt" title="暂无余额记录" />
  <div v-else class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>时间</th>
          <th>类型</th>
          <th class="right">金额</th>
          <th class="right">变动后余额</th>
          <th>说明</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in list.items" :key="t.id">
          <td class="nowrap num">{{ dateTime(t.created_at) }}</td>
          <td><StatusBadge :map="TX_TYPES" :value="t.type" /></td>
          <td class="right num nowrap" :class="t.amount >= 0 ? 'text-success' : 'text-danger'">
            <b>{{ money(t.amount, { sign: true }) }}</b>
          </td>
          <td class="right num nowrap">{{ money(t.balance_after) }}</td>
          <td>
            {{ t.note }}
            <div v-if="t.ref" class="cell-sub mono">{{ t.ref }}</div>
            <div v-if="t.operator" class="cell-sub">操作人：{{ t.operator }}</div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-if="list.total" class="card-footer">
    <Pagination :page="list.page" :total="list.total" :page-size="list.page_size" @change="list.load" />
  </div>
</template>

<script setup>
import EmptyState from '@/components/EmptyState.vue'
import Pagination from '@/components/Pagination.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { TX_TYPES } from '@/constants'
import { dateTime, money } from '@/utils/format'

// The balance ledger: a usePagedList() of billingApi.listTransactions, or of
// billingApi.adminListTransactions for administrators (whose rows also name the operator).
defineProps({
  list: { type: Object, required: true },
})
</script>
