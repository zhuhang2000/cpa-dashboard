<template>
  <SuggestInput v-model="tag" :options="options" maxlength="20" placeholder="选择已有标签或输入新标签" />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import SuggestInput from '@/components/base/SuggestInput.vue'
import { accountsApi } from '@/api/accounts'

// A tag field suggesting the tags in use, with how many users and managers carry each. id, required
// and the like fall through to the input.
const tag = defineModel({ type: String, default: '' })
const tags = ref([])
const options = computed(() =>
  tags.value.map((t) => ({ value: t.tag, hint: `${t.users} 位用户 · ${t.managers} 位管理员` })),
)

// A failed load only loses the suggestions.
onMounted(async () => {
  try {
    tags.value = (await accountsApi.adminListTags()).items
  } catch {
    tags.value = []
  }
})
</script>
