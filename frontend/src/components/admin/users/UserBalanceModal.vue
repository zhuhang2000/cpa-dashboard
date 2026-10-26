<template>
  <Modal open title="调整余额" :persistent="saving" @close="close">
    <form id="adjust-form" @submit.prevent="adjust">
      <p class="muted" style="margin-bottom: 14px">
        用户 <b style="color: var(--text)">{{ user.username }}</b> 当前余额
        <b class="num" style="color: var(--text)">{{ money(user.balance) }}</b>
      </p>
      <div class="field">
        <span class="field-label">操作</span>
        <div class="tabs">
          <button type="button" class="tab" :class="{ active: form.mode === 'add' }" @click="form.mode = 'add'">
            增加
          </button>
          <button type="button" class="tab" :class="{ active: form.mode === 'sub' }" @click="form.mode = 'sub'">
            扣减
          </button>
        </div>
      </div>
      <div v-if="form.mode === 'add' && canGift" class="field">
        <label for="adj-type">类型</label>
        <SelectMenu id="adj-type" v-model="form.type" :options="TYPE_OPTIONS" placeholder="请选择类型" />
      </div>
      <div class="field">
        <label for="adj-amount">金额</label>
        <div class="input-group has-prefix">
          <span class="input-prefix">{{ currency() }}</span>
          <input id="adj-amount" v-model="form.amount" class="input" type="number" min="0.01" step="0.01" required />
        </div>
        <div class="field-hint">{{ hint }}</div>
      </div>
      <div class="field">
        <label for="adj-note">备注</label>
        <input id="adj-note" v-model.trim="form.note" class="input" maxlength="100" placeholder="选填，用户可见" />
      </div>
    </form>
    <template #footer>
      <button class="btn" :disabled="saving" @click="close">取消</button>
      <button class="btn btn-primary" form="adjust-form" :disabled="saving">
        确认{{ form.mode === 'add' ? '增加' : '扣减' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import Modal from '@/components/base/Modal.vue'
import SelectMenu from '@/components/base/SelectMenu.vue'
import { billingApi } from '@/api/billing'
import { REDEEM_TYPES, RedeemType, Role } from '@/constants'
import { store } from '@/store'
import { currency, money } from '@/utils/format'
import { toast } from '@/toast'

const TYPE_OPTIONS = Object.entries(REDEEM_TYPES).map(([value, entry]) => ({ value, label: entry.label }))

const props = defineProps({ user: { type: Object, required: true } })
// `saved` asks the list to reload; `close` follows it, or comes from cancelling.
const emit = defineEmits(['close', 'saved'])
// Gifts create balance without payment: a tag manager only recharges, so it has no type to choose.
const canGift = store.user?.role === Role.ADMIN
const form = reactive({ mode: 'add', type: canGift ? '' : RedeemType.RECHARGE, amount: '', note: '' })
const saving = ref(false)

const hint = computed(() => {
  if (form.mode === 'sub') return '扣减余额，不抵扣充值统计，也不计入调用消费。'
  if (!form.type) return '请选择充值或赠送。'
  return form.type === RedeemType.GIFT ? '赠送仅增加余额，不计入充值统计。' : '充值增加余额，并计入充值统计。'
})

async function adjust() {
  if (saving.value) return
  if (form.mode === 'add' && !form.type) return toast.error('请选择充值或赠送')
  const value = Number(form.amount)
  if (!(value > 0)) return toast.error('请输入大于 0 的金额')
  saving.value = true
  try {
    const payload = { amount: form.mode === 'add' ? value : -value, note: form.note }
    if (form.mode === 'add') payload.type = form.type
    const data = await billingApi.adminAdjustBalance(props.user.id, payload)
    toast.success(`已调整，当前余额 ${money(data.balance)}`)
    emit('saved')
    emit('close')
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

// The dialog stays open until a submitted change returns, so its result is never lost.
function close() {
  if (!saving.value) emit('close')
}
</script>
