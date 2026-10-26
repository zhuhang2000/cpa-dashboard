<template>
  <Modal open title="设置标签" :persistent="saving" @close="close">
    <form id="tag-form" @submit.prevent="saveTags">
      <p class="muted" style="margin-bottom: 14px">
        为已选的 <b style="color: var(--text)">{{ ids.length }}</b> 位用户设置标签，并选择他们在标签中的身份。
      </p>
      <div class="field">
        <label for="tag-name">标签</label>
        <SuggestInput
          id="tag-name"
          v-model="tagName"
          :options="options"
          maxlength="20"
          placeholder="选择已有标签或输入新标签"
        />
      </div>
      <div class="field">
        <span class="field-label">身份</span>
        <div class="tabs">
          <button type="button" class="tab" :class="{ active: !manager }" @click="manager = false">成员</button>
          <button type="button" class="tab" :class="{ active: manager }" @click="manager = true">管理员</button>
        </div>
        <div class="field-hint">{{ hint }}</div>
      </div>
    </form>
    <template #footer>
      <button class="btn" :disabled="saving" @click="close">取消</button>
      <button class="btn btn-primary" form="tag-form" :disabled="saving">
        {{ tagName.trim() || manager ? '确认设置' : '清除标签' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Modal from '@/components/base/Modal.vue'
import SuggestInput from '@/components/base/SuggestInput.vue'
import { accountsApi } from '@/api/accounts'
import { toast } from '@/toast'

// The one place a tag is set: members join a group, and managers serve one.
// `ids` are the selected users, taken when the dialog opens.
const props = defineProps({ ids: { type: Array, required: true } })
// `saved` asks the list to reload; `close` follows it, or comes from cancelling.
const emit = defineEmits(['close', 'saved'])
const tagName = ref('')
const manager = ref(false)
const tags = ref([])
const saving = ref(false)

const options = computed(() =>
  tags.value.map((t) => ({ value: t.tag, hint: `${t.users} 位用户 · ${t.managers} 位管理员` })),
)
const hint = computed(() => {
  if (manager.value) return '只能进入用户管理，查看该标签下的普通用户，并为他们充值或扣款。'
  const effect = tagName.value.trim() ? '加入该标签，由负责它的管理员查看和充值' : '留空将清除这些用户的标签'
  return `${effect}；已是管理员的会改回普通用户。`
})

async function saveTags() {
  if (saving.value) return
  const tag = tagName.value.trim()
  if (manager.value && !tag) return toast.error('请填写管理员负责的标签')
  saving.value = true
  try {
    const { updated } = await accountsApi.adminTagUsers({ ids: props.ids, tag, manager: manager.value })
    if (manager.value) toast.success(`已将 ${updated} 位用户设为“${tag}”的管理员`)
    else toast.success(tag ? `已为 ${updated} 位用户设置标签` : `已清除 ${updated} 位用户的标签`)
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

// A failed load only loses the suggestions.
onMounted(async () => {
  try {
    tags.value = (await accountsApi.adminListTags()).items
  } catch {
    tags.value = []
  }
})
</script>
