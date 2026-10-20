<template>
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
      <div class="buy">
        <img :src="wechatQr" alt="管理员微信二维码" width="112" height="112" />
        <div>
          <div class="buy-title">还没有兑换码？</div>
          <p class="muted">
            微信扫码联系管理员购买。付款后管理员会发给你一串兑换码，填到上方输入框即可到账，每个兑换码仅可使用一次。
          </p>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import wechatQr from '@/assets/wechat-qr.jpg'
import Icon from '@/components/Icon.vue'
import { billingApi } from '@/api/billing'
import { money } from '@/utils/format'
import { toast } from '@/toast'

const emit = defineEmits(['redeemed'])
const code = ref('')
const redeeming = ref(false)

async function redeem() {
  redeeming.value = true
  try {
    const data = await billingApi.redeem({ code: code.value })
    toast.success(`兑换成功，到账 ${money(data.amount)}`)
    code.value = ''
    emit('redeemed')
  } catch (e) {
    toast.error(e.message)
  } finally {
    redeeming.value = false
  }
}
</script>

<style scoped>
.buy {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}
/* Keep the white quiet zone in dark mode too, or phones can't scan it. */
.buy img {
  flex: none;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.buy-title {
  font-weight: 600;
}
.buy p {
  margin-top: 4px;
  font-size: 12.5px;
}
</style>
