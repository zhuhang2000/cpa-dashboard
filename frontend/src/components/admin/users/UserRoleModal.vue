<template>
  <Modal open title="设置身份" :persistent="saving" @close="close">
    <form id="role-form" @submit.prevent="saveRole">
      <p class="muted" style="margin-bottom: 14px">
        用户 <b style="color: var(--text)">{{ user.username }}</b> 当前为{{ ROLES[user.role]?.label }}
      </p>
      <div class="field">
        <span class="field-label">身份</span>
        <div class="tabs">
          <button
            v-for="(entry, value) in ROLES"
            :key="value"
            type="button"
            class="tab"
            :class="{ active: form.role === value }"
            @click="form.role = value"
          >
            {{ entry.label }}
          </button>
        </div>
        <div class="field-hint">{{ ROLE_HINTS[form.role] }}</div>
      </div>
      <div v-if="form.role === Role.MANAGER" class="field">
        <label for="role-tag">负责的标签</label>
        <TagInput id="role-tag" v-model="form.tag" required />
      </div>
    </form>
    <template #footer>
      <button class="btn" :disabled="saving" @click="close">取消</button>
      <button class="btn btn-primary" form="role-form" :disabled="saving">确认</button>
    </template>
  </Modal>
</template>

<script setup>
import { reactive, ref } from 'vue'
import TagInput from './TagInput.vue'
import Modal from '@/components/base/Modal.vue'
import { accountsApi } from '@/api/accounts'
import { ROLES, Role } from '@/constants'
import { toast } from '@/toast'

const ROLE_HINTS = {
  [Role.USER]: '只能使用控制台，不能进入管理后台。',
  [Role.MANAGER]: '只能进入用户管理，查看带有所负责标签的普通用户，并为他们充值或扣款。',
  [Role.ADMIN]: '可以使用管理后台的全部功能。',
}

const props = defineProps({ user: { type: Object, required: true } })
// `saved` asks the list to reload; `close` follows it, or comes from cancelling.
const emit = defineEmits(['close', 'saved'])
const form = reactive({ role: props.user.role, tag: props.user.role === Role.MANAGER ? props.user.tag : '' })
const saving = ref(false)

async function saveRole() {
  if (saving.value) return
  const tag = form.tag.trim()
  if (form.role === Role.MANAGER && !tag) return toast.error('请填写负责的标签')
  saving.value = true
  try {
    const body = { role: form.role }
    if (form.role === Role.MANAGER) body.tag = tag
    await accountsApi.adminSetUserRole(props.user.id, body)
    toast.success(`已将 ${props.user.username} 设为${ROLES[form.role].label}`)
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
