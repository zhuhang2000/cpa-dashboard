<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">充值中心</h1>
        <p class="page-desc">为你的 AI 续航，随时接着用。</p>
      </div>
    </div>

    <div v-if="resultMessage" class="alert" :class="resultOk ? 'alert-success' : 'alert-warning'">
      <Icon :name="resultOk ? 'check-circle' : 'clock'" :size="16" />
      <div class="alert-body">{{ resultMessage }}</div>
      <button class="alert-close" aria-label="关闭" @click="resultMessage = ''"><Icon name="x" :size="16" /></button>
    </div>

    <div class="wallet" :class="{ 'has-online': online }">
      <section class="card balance-card" aria-label="账户额度">
        <div class="balance-main">
          <div class="balance-head">
            <div class="balance-label">当前可用额度</div>
            <div class="balance-value num" :class="{ 'text-danger': balance <= 0 }">
              {{ money(balance) }}
            </div>
            <span class="badge plain balance-tag"><Icon name="zap" :size="13" />按量扣费 · 余额不过期</span>
          </div>
          <SpendTrend class="balance-trend" />
          <div class="balance-stats">
            <div>
              <span>累计充值</span><b class="num">{{ money(user.total_recharge || 0) }}</b>
            </div>
            <div>
              <span>累计消费</span><b class="num">{{ money(user.total_spent || 0) }}</b>
            </div>
          </div>
        </div>
      </section>
      <RedeemCard class="wallet-redeem" @redeemed="onRedeemed" />
      <OnlinePayCard v-if="online" class="wallet-online" :payment="payment" />
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">余额记录</div>
        <div v-if="online" class="tabs">
          <button class="tab" :class="{ active: tab === 'tx' }" @click="switchTab('tx')">余额流水</button>
          <button class="tab" :class="{ active: tab === 'orders' }" @click="switchTab('orders')">支付订单</button>
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
import TransactionTable from '@/components/shared/TransactionTable.vue'
import OnlinePayCard from '@/components/billing/OnlinePayCard.vue'
import OrderTable from '@/components/billing/OrderTable.vue'
import RedeemCard from '@/components/billing/RedeemCard.vue'
import SpendTrend from '@/components/billing/SpendTrend.vue'
import { billingApi } from '@/api/billing'
import { usePagedList } from '@/composables/usePagedList'
import { refreshUser, siteStore, sessionStore } from '@/stores'
import { money } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const payment = computed(() => siteStore.status?.payment || { online: false, channels: [], presets: [] })
const online = computed(() => payment.value.online)
const user = computed(() => sessionStore.user || {})
const balance = computed(() => Number(user.value.balance) || 0)
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
/* Balance on the left, recharge on the right, stretched to one height so their tops and bottoms line up.
   With online pay enabled it takes the right column and the redeem card moves under the balance. */
.wallet {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.wallet.has-online {
  grid-template-areas:
    'balance online'
    'redeem online';
}
.has-online .balance-card {
  grid-area: balance;
}
.has-online .wallet-redeem {
  grid-area: redeem;
}
.has-online .wallet-online {
  grid-area: online;
}

.balance-card {
  display: flex;
  flex-direction: column;
  container-type: inline-size;
}
/* Amount and usage-rule tag top-left, totals pinned to the bottom-left; the 7-day spend curve fills the
   full height on the right, so extra height from the row grows the chart. Stacked when the card is narrow. */
.balance-main {
  flex: 1;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  grid-template-rows: auto 1fr;
  grid-template-areas:
    'head trend'
    'stats trend';
  gap: 30px 32px;
  padding: 20px 24px;
}
.balance-head {
  grid-area: head;
}
.balance-trend {
  grid-area: trend;
}
@container (max-width: 460px) {
  .balance-main {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: none;
    grid-template-areas: 'head' 'trend' 'stats';
  }
}
.balance-label {
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
}
.balance-value {
  margin-top: 8px;
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
}
.balance-tag {
  margin-left: -10px;
  margin-top: 10px;
}
.balance-stats {
  grid-area: stats;
  align-self: end;
  display: flex;
  flex-wrap: wrap;
  row-gap: 8px;
}
.balance-stats > div {
  padding-right: 20px;
}
.balance-stats > div + div {
  padding-left: 20px;
  border-left: 1px solid var(--border);
}
.balance-stats span {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.balance-stats b {
  display: block;
  margin-top: 2px;
  font-size: 15px;
  font-weight: 600;
}
@media (max-width: 900px) {
  .wallet {
    grid-template-columns: minmax(0, 1fr);
  }
  .wallet.has-online {
    grid-template-areas: 'balance' 'online' 'redeem';
  }
}
@media (max-width: 560px) {
  .balance-main {
    padding: 18px 16px 16px;
  }
  .balance-value {
    font-size: 30px;
  }
}
</style>
