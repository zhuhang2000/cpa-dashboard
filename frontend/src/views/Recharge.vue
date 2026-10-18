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
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">兑换码充值</div>
            <div class="card-sub">输入兑换码，面额立即到账</div>
          </div>
          <span class="stat-icon green"><Icon name="ticket" :size="16" /></span>
        </div>
        <form class="card-body" @submit.prevent="redeem">
          <div class="field">
            <label for="code">兑换码</label>
            <input
              id="code"
              v-model.trim="code"
              class="input mono"
              placeholder="XXXX-XXXX-XXXX-XXXX"
              autocomplete="off"
              spellcheck="false"
              style="letter-spacing: 0.06em; text-transform: uppercase"
            />
          </div>
          <button class="btn btn-primary btn-block" :disabled="redeeming || !code">
            <Icon v-if="redeeming" name="loader" :size="16" />
            {{ redeeming ? '兑换中…' : '立即兑换' }}
          </button>
          <p class="muted" style="font-size: 12.5px; margin-top: 12px">
            兑换码可向管理员或授权渠道购买，每个兑换码仅可使用一次。
          </p>
        </form>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">在线充值</div>
            <div class="card-sub">{{ online ? '选择金额与支付方式，支付完成后自动到账' : '暂未开放' }}</div>
          </div>
          <span class="stat-icon blue"><Icon name="card" :size="16" /></span>
        </div>
        <div v-if="!online" class="card-body">
          <EmptyState icon="card" title="在线支付暂未开放" desc="请使用兑换码充值，或联系管理员获取兑换码" />
        </div>
        <form v-else class="card-body" @submit.prevent="pay">
          <div class="field">
            <span class="field-label">充值金额</span>
            <div class="amounts">
              <button
                v-for="p in presets"
                :key="p"
                type="button"
                class="amount"
                :class="{ active: !customAmount && amount === p }"
                @click="pick(p)"
              >
                <b class="num">{{ currency() }}{{ p }}</b>
                <span v-if="ratio !== 1" class="cell-sub">到账 {{ money(p * ratio) }}</span>
              </button>
            </div>
          </div>
          <div class="field">
            <label for="custom-amount">自定义金额</label>
            <div class="input-group has-prefix">
              <span class="input-prefix">{{ currency() }}</span>
              <input
                id="custom-amount"
                v-model="customAmount"
                class="input"
                type="number"
                :min="payment.min_amount"
                :max="payment.max_amount"
                step="0.01"
                :placeholder="`${payment.min_amount} - ${payment.max_amount}`"
              />
            </div>
          </div>
          <div class="field">
            <span class="field-label">支付方式</span>
            <div class="row wrap">
              <button
                v-for="c in payment.channels"
                :key="c"
                type="button"
                class="channel"
                :class="{ active: channel === c }"
                @click="channel = c"
              >
                <span class="dot" :class="c" />{{ PAY_CHANNELS[c] || c }}
              </button>
            </div>
          </div>
          <button class="btn btn-primary btn-block btn-lg" :disabled="paying || !finalAmount">
            <Icon v-if="paying" name="loader" :size="16" />
            {{ paying ? '正在跳转…' : `支付 ${currency()}${finalAmount || 0}` }}
          </button>
        </form>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">充值记录</div>
        <div class="tabs">
          <button class="tab" :class="{ active: tab === 'tx' }" @click="switchTab('tx')">余额流水</button>
          <button v-if="online" class="tab" :class="{ active: tab === 'orders' }" @click="switchTab('orders')">
            支付订单
          </button>
        </div>
      </div>
      <template v-if="tab === 'tx'">
        <div v-if="tx.loading && !tx.items.length" class="card-body stack" style="gap: 10px">
          <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
        </div>
        <EmptyState v-else-if="!tx.items.length" icon="receipt" title="暂无充值记录" />
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
              <tr v-for="t in tx.items" :key="t.id">
                <td class="nowrap num">{{ dateTime(t.created_at) }}</td>
                <td><StatusBadge :map="TX_TYPES" :value="t.type" /></td>
                <td class="right num nowrap" :class="t.amount >= 0 ? 'text-success' : 'text-danger'">
                  <b>{{ money(t.amount, { sign: true }) }}</b>
                </td>
                <td class="right num nowrap">{{ money(t.balance_after) }}</td>
                <td>
                  {{ t.note }}
                  <div v-if="t.ref" class="cell-sub mono">{{ t.ref }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="tx.total" class="card-footer">
          <Pagination :page="tx.page" :total="tx.total" :page-size="tx.page_size" @change="tx.load" />
        </div>
      </template>
      <template v-else>
        <div v-if="orders.loading && !orders.items.length" class="card-body stack" style="gap: 10px">
          <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
        </div>
        <EmptyState v-else-if="!orders.items.length" icon="receipt" title="暂无支付订单" />
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
              <tr v-for="o in orders.items" :key="o.order_no">
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
        <div v-if="orders.total" class="card-footer">
          <Pagination :page="orders.page" :total="orders.total" :page-size="orders.page_size" @change="orders.load" />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import Pagination from '@/components/Pagination.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api'
import { usePagedList } from '@/composables/usePagedList'
import { ORDER_STATUSES, PAY_CHANNELS, TX_TYPES } from '@/constants'
import { refreshUser, store } from '@/store'
import { currency, dateTime, money } from '@/utils/format'
import { toast } from '@/toast'

const route = useRoute()
const router = useRouter()
const payment = computed(() => store.status?.payment || { online: false, channels: [], presets: [] })
const online = computed(() => payment.value.online)
const presets = computed(() => payment.value.presets || [])
const ratio = computed(() => Number(payment.value.credit_ratio) || 1)

const code = ref('')
const redeeming = ref(false)
const amount = ref(presets.value[1] ?? presets.value[0] ?? 10)
const customAmount = ref('')
const channel = ref(payment.value.channels?.[0] || '')
const paying = ref(false)
const tab = ref('tx')
const tx = usePagedList('/api/billing/transactions')
const orders = usePagedList('/api/billing/orders')
const resultMessage = ref('')
const resultOk = ref(false)

const finalAmount = computed(() => {
  const v = customAmount.value !== '' ? Number(customAmount.value) : amount.value
  return Number.isFinite(v) && v > 0 ? Math.floor(v * 100) / 100 : 0
})

function pick(p) {
  amount.value = p
  customAmount.value = ''
}

async function redeem() {
  redeeming.value = true
  try {
    const data = await api.post('/api/billing/redeem', { code: code.value })
    toast.success(`兑换成功，到账 ${money(data.amount)}`)
    code.value = ''
    await Promise.all([refreshUser(), tx.load(1)])
  } catch (e) {
    toast.error(e.message)
  } finally {
    redeeming.value = false
  }
}

async function pay() {
  const value = finalAmount.value
  const { min_amount: min, max_amount: max } = payment.value
  if (value < min || value > max) {
    toast.error(`充值金额需在 ${min} - ${max} 之间`)
    return
  }
  paying.value = true
  try {
    const data = await api.post('/api/billing/orders', { amount: value.toFixed(2), channel: channel.value })
    window.location.href = data.pay_url
  } catch (e) {
    toast.error(e.message)
    paying.value = false
  }
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
.amounts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.amount {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 56px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-size: 15px;
}
.amount:hover {
  border-color: var(--accent);
}
.amount.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-text);
  box-shadow: 0 0 0 1px var(--accent) inset;
}
.channel {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 16px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-weight: 500;
}
.channel.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent) inset;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--faint);
}
.dot.alipay {
  background: #1677ff;
}
.dot.wxpay {
  background: #07c160;
}
.dot.qqpay {
  background: #12b7f5;
}
</style>
