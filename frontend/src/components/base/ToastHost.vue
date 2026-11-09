<template>
  <div class="toast-host" aria-live="polite">
    <TransitionGroup name="toast" @before-leave="pin">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
        <Icon :name="icons[t.type]" :size="18" />
        <span>{{ t.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'
import { toasts } from '@/toast'

const icons = { success: 'check-circle', error: 'x-circle', info: 'info' }

// 离开的提示会脱离布局 (.toast-leave-active)。先按它现在的位置和宽度固定住：错误提示停留得更久，
// 离开的不一定是最上面那条，不固定会跳到顶部；容器随之变窄时也不会重新换行。
function pin(el) {
  el.style.top = `${el.offsetTop}px`
  el.style.width = `${el.offsetWidth}px`
}
</script>
