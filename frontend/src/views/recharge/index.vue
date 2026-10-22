<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">充值中心</h1>
        <p class="page-desc">余额按实际调用扣费，充值后已暂停的密钥会在几秒内自动恢复。</p>
      </div>
    </div>

    <div v-if="resultMessage" class="alert" :class="resultOk ? 'alert-success' : 'alert-warning'">
      <Icon :name="resultOk ? 'check-circle' : 'clock'" :size="16" />
      <div class="alert-body">{{ resultMessage }}</div>
      <button class="alert-close" aria-label="关闭" @click="resultMessage = ''"><Icon name="x" :size="16" /></button>
    </div>

    <div class="balance-hero card">
      <div>
        <div class="muted">当前余额</div>
        <div class="balance-value num" :class="{ 'text-danger': (store.user?.balance ?? 0) <= 0 }">
          {{ money(store.user?.balance || 0) }}
        </div>
      </div>
      <div class="balance-meta">
        <div>
          <div class="muted">累计充值</div>
          <b class="num">{{ money(store.user?.total_recharge || 0) }}</b>
        </div>
        <div>
          <div class="muted">累计消费</div>
          <b class="num">{{ money(store.user?.total_spent || 0) }}</b>
        </div>
      </div>
    </div>

    <div class="grid grid-2">
      <RedeemCard @redeemed="onRedeemed" />
      <OnlinePayCard :payment="payment" />
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">余额记录</div>
        <div class="tabs">
          <button class="tab" :class="{ active: tab === 'tx' }" @click="switchTab('tx')">余额流水</button>
          <button v-if="online" class="tab" :class="{ active: tab === 'orders' }" @click="switchTab('orders')">
            支付订单
          </button>
        </div>
      </div>
      <TransactionTable v-if="tab === 'tx'" :list="tx" />
      <OrderTable v-else :list="orders" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '@/components/base/Icon.vue'
import OnlinePayCard from './OnlinePayCard.vue'
import OrderTable from './OrderTable.vue'
import RedeemCard from './RedeemCard.vue'
import TransactionTable from './TransactionTable.vue'
import { billingApi } from '@/api/billing'
import { usePagedList } from '@/composables/usePagedList'
import { refreshUser, store } from '@/store'
import { money } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const payment = computed(() => store.status?.payment || { online: false, channels: [], presets: [] })
const online = computed(() => payment.value.online)
const tab = ref('tx')
const tx = usePagedList(billingApi.listTransactions)
const orders = usePagedList(billingApi.listOrders)
const resultMessage = ref('')
const resultOk = ref(false)

// A redeemed code changes the balance and adds a ledger entry.
function onRedeemed() {
  refreshUser()
  tx.load(1)
}

function switchTab(t) {
  tab.value = t
  if (t === 'orders') orders.load(1)
}

onMounted(() => {
  const { order, result } = route.query
  if (order) {
    resultOk.value = result === 'success'
    resultMessage.value = resultOk.value
      ? `支付成功，订单 ${order} 已到账。`
      : `订单 ${order} 尚未确认到账，通常几秒内完成，可稍后在“支付订单”中查看。`
    router.replace({ query: {} })
    if (online.value) tab.value = 'orders'
  }
  refreshUser()
  tx.load(1)
  if (tab.value === 'orders') orders.load(1)
})
</script>

<style scoped>
.balance-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding: 22px 24px;
  background: radial-gradient(600px 180px at 0% 0%, var(--accent-soft), transparent 70%), var(--surface);
}
.balance-value {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-top: 2px;
}
.balance-meta {
  display: flex;
  gap: 40px;
}
.balance-meta b {
  font-size: 17px;
}
</style>
