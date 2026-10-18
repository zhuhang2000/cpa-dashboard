<template>
  <button
    type="button"
    class="btn"
    :class="[variant === 'ghost' ? 'btn-ghost' : '', size === 'sm' ? 'btn-sm' : '', label ? '' : 'btn-icon']"
    :title="label || '复制'"
    @click.stop="copy"
  >
    <Icon :name="copied ? 'check' : 'copy'" :size="size === 'sm' ? 15 : 16" />
    <span v-if="label">{{ copied ? '已复制' : label }}</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import Icon from './Icon.vue'
import { copyLazy, copyText, toast } from '../toast'

const props = defineProps({
  text: { type: [String, Function], required: true },
  label: { type: String, default: '' },
  size: { type: String, default: 'sm' },
  variant: { type: String, default: 'ghost' },
})

const copied = ref(false)
let timer = null

async function copy() {
  let ok
  if (typeof props.text === 'function') {
    ok = await copyLazy(Promise.resolve(props.text()))
    if (ok === null) return
  } else {
    if (!props.text) return
    ok = await copyText(props.text)
  }
  if (ok) {
    copied.value = true
    clearTimeout(timer)
    timer = setTimeout(() => (copied.value = false), 1600)
    if (!props.label) toast.success('已复制到剪贴板')
  } else {
    toast.error('复制失败，请手动选择复制')
  }
}
</script>
