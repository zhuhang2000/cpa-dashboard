<template>
  <div class="card">
    <div class="card-header">
      <div>
        <div class="card-title">在线充值</div>
        <div class="card-sub">{{ payment.online ? '选择金额与支付方式，支付完成后自动到账' : '暂未开放' }}</div>
      </div>
      <span class="stat-icon blue"><Icon name="card" :size="16" /></span>
    </div>
    <div v-if="!payment.online" class="card-body">
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
</template>

<script setup>
import { computed, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import { billingApi } from '@/api/billing'
import { PAY_CHANNELS } from '@/constants'
import { currency, money } from '@/utils/format'
import { toast } from '@/toast'

// store.status.payment: online, channels, presets, min_amount, max_amount, credit_ratio.
const props = defineProps({
  payment: { type: Object, required: true },
})

const presets = computed(() => props.payment.presets || [])
const ratio = computed(() => Number(props.payment.credit_ratio) || 1)
const amount = ref(presets.value[1] ?? presets.value[0] ?? 10)
const customAmount = ref('')
const channel = ref(props.payment.channels?.[0] || '')
const paying = ref(false)

const finalAmount = computed(() => {
  const v = customAmount.value !== '' ? Number(customAmount.value) : amount.value
  return Number.isFinite(v) && v > 0 ? Math.floor(v * 100) / 100 : 0
})

function pick(p) {
  amount.value = p
  customAmount.value = ''
}

async function pay() {
  const value = finalAmount.value
  const { min_amount: min, max_amount: max } = props.payment
  if (value < min || value > max) {
    toast.error(`充值金额需在 ${min} - ${max} 之间`)
    return
  }
  paying.value = true
  try {
    const data = await billingApi.createOrder({ amount: value.toFixed(2), channel: channel.value })
    window.location.href = data.pay_url
  } catch (e) {
    toast.error(e.message)
    paying.value = false
  }
}
</script>

<style scoped>
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
