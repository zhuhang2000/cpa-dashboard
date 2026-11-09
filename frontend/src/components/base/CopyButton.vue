<template>
  <button
    type="button"
    class="btn btn-ghost btn-sm"
    :class="{ 'btn-icon': !label }"
    :title="label || '复制'"
    @click.stop="copy"
  >
    <Transition name="swap" mode="out-in">
      <Icon :key="copied" :name="copied ? 'check' : 'copy'" :size="15" />
    </Transition>
    <span v-if="label">{{ copied ? '已复制' : label }}</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import Icon from './Icon.vue'
import { toast } from '@/toast'
import { copyLazy, copyText } from '@/utils/clipboard'

const props = defineProps({
  // 字符串直接复制；函数需返回 Promise（如按需拉取的密钥），失败时由其自行提示并返回空值
  text: { type: [String, Function], required: true },
  label: { type: String, default: '' },
})

const copied = ref(false)

// 对勾与 toast 同进同出：toast 弹出时对勾弹入，toast 开始淡出时复制图标弹回。对勾期间再点不重复复制。
async function copy() {
  if (copied.value) return
  const ok = typeof props.text === 'function' ? await copyLazy(props.text()) : await copyText(props.text)
  if (ok === null) return
  if (!ok) return toast.error('复制失败，请手动选择复制')
  copied.value = true
  await toast.success('已复制到剪贴板')
  copied.value = false
}
</script>

<style scoped>
/* 与 toast 的 pop-in 同时长，略带回弹 */
.swap-enter-active {
  transition:
    opacity 0.2s ease-out,
    transform 0.23s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.swap-enter-from {
  opacity: 0;
  transform: scale(0.5);
}
</style>
