<template>
  <Modal open title="设置标签" :persistent="saving" @close="close">
    <form id="tag-form" @submit.prevent="saveTags">
      <p class="muted" style="margin-bottom: 14px">
        为已选的 <b style="color: var(--text)">{{ ids.length }}</b>
        位普通用户设置标签，负责该标签的管理员即可查看并为他们充值。
      </p>
      <div class="field">
        <label for="tag-name">标签</label>
        <TagInput id="tag-name" v-model="tagName" />
        <div class="field-hint">留空并确认将清除这些用户的标签。</div>
      </div>
    </form>
    <template #footer>
      <button class="btn" :disabled="saving" @click="close">取消</button>
      <button class="btn btn-primary" form="tag-form" :disabled="saving">
        {{ tagName.trim() ? '确认设置' : '清除标签' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref } from 'vue'
import TagInput from './TagInput.vue'
import Modal from '@/components/base/Modal.vue'
import { accountsApi } from '@/api/accounts'
import { toast } from '@/toast'

// `ids` are the selected users, taken when the dialog opens.
const props = defineProps({ ids: { type: Array, required: true } })
// `saved` asks the list to reload; `close` follows it, or comes from cancelling.
const emit = defineEmits(['close', 'saved'])
const tagName = ref('')
const saving = ref(false)

async function saveTags() {
  if (saving.value) return
  const tag = tagName.value.trim()
  saving.value = true
  try {
    const { updated } = await accountsApi.adminTagUsers({ ids: props.ids, tag })
    toast.success(tag ? `已为 ${updated} 位用户设置标签` : `已清除 ${updated} 位用户的标签`)
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
