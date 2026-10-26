<template>
  <Modal open title="重置密码" :persistent="saving" @close="close">
    <form id="reset-form" @submit.prevent="resetPassword">
      <p class="muted" style="margin-bottom: 14px">
        为用户 <b style="color: var(--text)">{{ user.username }}</b> 设置新密码，重置后该用户需重新登录。
      </p>
      <div class="field">
        <label for="reset-pass">新密码</label>
        <PasswordInput
          id="reset-pass"
          v-model="password"
          autocomplete="new-password"
          minlength="8"
          maxlength="128"
          placeholder="至少 8 位"
          required
        />
        <div class="field-hint">请通过安全渠道将新密码告知用户，并提醒其登录后在个人设置中修改。</div>
      </div>
    </form>
    <template #footer>
      <button class="btn" :disabled="saving" @click="close">取消</button>
      <button class="btn btn-primary" form="reset-form" :disabled="saving">确认重置</button>
    </template>
  </Modal>
</template>

<script setup>
import { ref } from 'vue'
import Modal from '@/components/base/Modal.vue'
import PasswordInput from '@/components/base/PasswordInput.vue'
import { accountsApi } from '@/api/accounts'
import { toast } from '@/toast'

const props = defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['close'])
const password = ref('')
const saving = ref(false)

async function resetPassword() {
  if (saving.value) return
  if (password.value.length < 8) return toast.error('密码至少 8 位')
  saving.value = true
  try {
    await accountsApi.adminResetPassword(props.user.id, { password: password.value })
    toast.success(`已重置 ${props.user.username} 的密码`)
    emit('close')
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

// The dialog stays open until a submitted reset returns, so its result is never lost.
function close() {
  if (!saving.value) emit('close')
}
</script>
