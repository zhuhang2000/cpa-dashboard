<template>
  <form @submit.prevent="submit">
    <label v-if="label" :for="inputId" class="notice-editor-label">{{ label }}</label>
    <textarea
      :id="inputId"
      ref="input"
      v-model="draft"
      class="textarea"
      :class="{ 'notice-editor': label }"
      rows="4"
      maxlength="2000"
      :aria-label="label || '公告内容'"
      :disabled="saving"
      placeholder="第一行填写公告标题，换行后填写详细内容"
    />
    <div class="notice-editor-foot">
      <span v-if="hint" class="field-hint">{{ hint }}</span>
      <button type="button" class="btn btn-sm" :disabled="saving" @click="emit('cancel')">取消</button>
      <button type="submit" class="btn btn-sm btn-primary" :disabled="saving || !draft.trim()">
        {{ submitLabel }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { onMounted, ref, useId } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  submitLabel: { type: String, default: '保存' },
  saving: Boolean,
})
const draft = defineModel({ type: String, required: true })
const emit = defineEmits(['submit', 'cancel'])
const inputId = useId()
const input = ref(null)

onMounted(() => input.value?.focus())

function submit() {
  if (!props.saving && draft.value.trim()) emit('submit', draft.value)
}
</script>

<style scoped>
.notice-editor {
  margin-top: 8px;
}
.notice-editor-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.notice-editor-foot .field-hint {
  flex: 1;
  margin: 0;
}

.notice-editor-label {
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 480px) {
  .notice-editor-foot {
    flex-wrap: wrap;
  }
  .notice-editor-foot .field-hint {
    flex-basis: 100%;
  }
}
</style>
