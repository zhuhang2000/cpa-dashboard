<template>
  <button
    class="btn btn-ghost btn-icon notice-btn"
    :title="notices.unread ? '有新通知' : '公告中心'"
    :aria-label="notices.unread ? '公告中心（有新通知）' : '公告中心'"
    aria-haspopup="dialog"
    @click="show"
  >
    <Icon name="bell" />
    <span v-if="notices.unread" class="notice-dot" />
  </button>

  <NoticeDialog v-if="open" :notices="notices" @close="open = false" />
</template>

<script setup>
import { ref } from 'vue'
import Icon from '@/components/base/Icon.vue'
import { useNotices } from '@/composables/useNotices'
import NoticeDialog from './NoticeDialog.vue'

const notices = useNotices()
const open = ref(false)

function show() {
  open.value = true
  notices.load()
}
</script>

<style scoped>
.notice-btn {
  position: relative;
}
.notice-dot {
  position: absolute;
  top: 7px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
  box-shadow: 0 0 0 2px var(--bg);
}
/* A ripple around the dot so a new notice is hard to miss. */
.notice-dot::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: var(--danger);
  animation: notice-ping 1.6s ease-out infinite;
}
@keyframes notice-ping {
  75%,
  100% {
    transform: scale(2.4);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .notice-dot::after {
    animation: none;
  }
}
</style>
