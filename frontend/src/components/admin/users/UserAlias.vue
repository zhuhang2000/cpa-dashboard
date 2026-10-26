<template>
  <button
    v-if="user.alias"
    type="button"
    class="alias"
    title="修改别名"
    :aria-label="`修改 ${user.username} 的别名：${user.alias}`"
    @click="open"
  >
    {{ user.alias }}<Icon name="pencil" :size="12" />
  </button>
  <button
    v-else
    type="button"
    class="link-btn alias-add"
    title="设置别名"
    :aria-label="`设置 ${user.username} 的别名`"
    @click="open"
  >
    <Icon name="pencil" :size="13" />
  </button>

  <Modal v-if="editing" open title="设置别名" :persistent="saving" @close="close">
    <form :id="`${uid}-form`" @submit.prevent="save">
      <p class="muted" style="margin-bottom: 14px">
        为用户 <b style="color: var(--text)">{{ user.username }}</b> 设置别名，方便在列表中识别和搜索。
      </p>
      <div class="field">
        <label :for="`${uid}-input`">别名</label>
        <input
          :id="`${uid}-input`"
          v-model="alias"
          class="input"
          maxlength="20"
          placeholder="例如：真实姓名、所在单位"
        />
        <div class="field-hint">只在管理后台显示，用户本人看不到。留空并确认将清除别名。</div>
      </div>
    </form>
    <template #footer>
      <button class="btn" :disabled="saving" @click="close">取消</button>
      <button class="btn btn-primary" :form="`${uid}-form`" :disabled="saving || unchanged">
        {{ alias.trim() || !user.alias ? '确认设置' : '清除别名' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import Icon from '@/components/base/Icon.vue'
import Modal from '@/components/base/Modal.vue'
import { accountsApi } from '@/api/accounts'
import { toast } from '@/toast'

// A user's alias, or a pencil to add one, together with the dialog that edits it.
const props = defineProps({ user: { type: Object, required: true } })
// `saved` asks the list to reload with the new alias.
const emit = defineEmits(['saved'])
const uid = useId() // every row has one, so the form needs its own ids
const editing = ref(false)
const alias = ref('')
const saving = ref(false)
const unchanged = computed(() => alias.value.trim() === props.user.alias)

// Each opening starts from the alias as listed, not from what was typed last time.
function open() {
  alias.value = props.user.alias
  editing.value = true
}

async function save() {
  if (saving.value || unchanged.value) return
  saving.value = true
  try {
    // The server tidies the spacing, so the message shows the alias as saved.
    const saved = (await accountsApi.adminSetUserAlias(props.user.id, { alias: alias.value })).alias
    toast.success(saved ? `已将 ${props.user.username} 的别名设为“${saved}”` : `已清除 ${props.user.username} 的别名`)
    editing.value = false
    emit('saved')
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

// The dialog stays open until a submitted change returns, so its result is never lost.
function close() {
  if (!saving.value) editing.value = false
}
</script>

<style scoped>
.alias-add {
  display: inline-flex;
  color: var(--muted);
}
.alias-add:hover {
  color: var(--accent);
}
/* The alias is the one label staff edit in place, so it is a tinted button rather than another badge. */
.alias {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 22px;
  padding: 0 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.alias:hover {
  border-color: color-mix(in srgb, var(--accent) 35%, transparent);
}
</style>
