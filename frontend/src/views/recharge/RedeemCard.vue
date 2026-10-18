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
      <p class="muted" style="font-size: 12.5px; margin-top: 12px">
        兑换码可向管理员或授权渠道购买，每个兑换码仅可使用一次。
      </p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
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
