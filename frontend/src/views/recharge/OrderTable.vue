<template>
  <div v-if="list.loading && !list.items.length" class="card-body stack" style="gap: 10px">
    <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
  </div>
  <EmptyState v-else-if="!list.items.length" icon="receipt" title="暂无支付订单" />
  <div v-else class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>订单号</th>
          <th>支付方式</th>
          <th class="right">支付金额</th>
          <th class="right">到账</th>
          <th>状态</th>
          <th>创建时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in list.items" :key="o.order_no">
          <td class="mono nowrap">{{ o.order_no }}</td>
          <td>{{ PAY_CHANNELS[o.channel] || o.channel }}</td>
          <td class="right num">{{ currency() }}{{ o.pay_amount }}</td>
          <td class="right num">{{ money(o.credit) }}</td>
          <td><StatusBadge :map="ORDER_STATUSES" :value="o.status" /></td>
          <td class="nowrap num">{{ dateTime(o.created_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-if="list.total" class="card-footer">
    <Pagination :page="list.page" :total="list.total" :page-size="list.page_size" @change="list.load" />
  </div>
</template>

<script setup>
import EmptyState from '@/components/base/EmptyState.vue'
import Pagination from '@/components/base/Pagination.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { ORDER_STATUSES, PAY_CHANNELS } from '@/constants'
import { currency, dateTime, money } from '@/utils/format'

// Online payment orders: a usePagedList() of billingApi.listOrders.
defineProps({
  list: { type: Object, required: true },
})
</script>
