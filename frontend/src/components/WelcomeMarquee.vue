<template>
  <div
    v-if="visible"
    ref="root"
    class="welcome-bar"
    :class="{ unplaced: !pos }"
    :style="pos && { left: `${pos.left}px`, maxWidth: `min(640px, ${pos.maxWidth}px)` }"
  >
    <Icon name="megaphone" :size="15" class="welcome-icon" />
    <div class="welcome-viewport">
      <div class="welcome-track" :style="{ animationDuration: `${duration}s` }">
        <span ref="item" class="welcome-item">
          {{ greeting }}，{{ store.user.username }}！本站价格<strong>与官方完全一致</strong>，充
          <strong>1 元当 1 美元</strong>花。
        </span>
        <span class="welcome-item welcome-copy" aria-hidden="true">
          {{ greeting }}，{{ store.user.username }}！本站价格<strong>与官方完全一致</strong>，充
          <strong>1 元当 1 美元</strong>花。
        </span>
      </div>
    </div>
    <button class="welcome-close" aria-label="关闭欢迎提示" title="关闭" @click="close">
      <Icon name="x" :size="14" />
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Icon from '@/components/Icon.vue'
import { store } from '@/store'

// Scroll speed in px/s.
const SPEED = 40
// Space kept from the page title and the topbar's right-hand controls, and the narrowest the bar may get.
const GAP = 12
const MIN_WIDTH = 200
const STORAGE_KEY = 'portal-welcome-closed'

const route = useRoute()
const hour = new Date().getHours()
const greeting = hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'

// Closing hides the bar for the current sign-in only: every login bumps last_login_at, so the next one shows it again.
const session = computed(() => `${store.user?.id}:${store.user?.last_login_at}`)
const closedFor = ref(readClosed())
const visible = computed(() => !!store.user && closedFor.value !== session.value)

// One loop scrolls exactly one copy of the text, so the duration follows its width.
const item = ref(null)
const duration = ref(12)

// The bar is laid over the topbar with its left edge on the page content's left edge, so it lines up
// with the cards and announcement below. Where that edge would hit the page title (narrow screens) it
// starts just after the title instead, and it is hidden when too little room is left before the controls.
const root = ref(null)
const pos = ref(null)
let observer = null

function align() {
  const bar = root.value
  if (!bar) return
  const topbar = bar.parentElement
  const content = topbar.parentElement.querySelector('.content')
  const title = document.createRange()
  title.selectNodeContents(topbar.querySelector('.topbar-title'))
  const box = topbar.getBoundingClientRect()
  const contentLeft = content.getBoundingClientRect().left + parseFloat(getComputedStyle(content).paddingLeft)
  const left = Math.max(contentLeft, title.getBoundingClientRect().right + GAP) - box.left
  const maxWidth = topbar.querySelector('.topbar-right').getBoundingClientRect().left - GAP - box.left - left
  pos.value = maxWidth >= MIN_WIDTH ? { left, maxWidth } : null
}

onMounted(() => {
  if (!root.value) return
  duration.value = item.value.offsetWidth / SPEED
  const topbar = root.value.parentElement
  observer = new ResizeObserver(align)
  observer.observe(topbar)
  observer.observe(topbar.querySelector('.topbar-right'))
})
onBeforeUnmount(() => observer?.disconnect())
watch(() => route.meta.title, align, { flush: 'post' })

function readClosed() {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function close() {
  closedFor.value = session.value
  try {
    localStorage.setItem(STORAGE_KEY, session.value)
  } catch {
    /* ignore */
  }
}
</script>

<style scoped>
.welcome-bar {
  position: absolute;
  top: 50%;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 4px 0 12px;
  border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent);
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 13px;
  transform: translateY(-50%);
}
/* Hidden but still laid out so its text can be measured; anchored right so it cannot widen the page. */
.welcome-bar.unplaced {
  right: 0;
  visibility: hidden;
}
.welcome-icon {
  flex: none;
}
.welcome-viewport {
  min-width: 0;
  overflow: hidden;
  /* Fade the text in and out at the edges instead of cutting it off. */
  mask-image: linear-gradient(90deg, transparent, #000 16px, #000 calc(100% - 16px), transparent);
}
/* The second copy is positioned out of flow, so the bar is as wide as one copy and the
   loop (shifting by one copy width) is seamless. */
.welcome-track {
  position: relative;
  width: max-content;
  animation: welcome-scroll 12s linear infinite;
}
.welcome-bar:hover .welcome-track {
  animation-play-state: paused;
}
.welcome-item {
  display: inline-block;
  padding: 0 40px 0 16px;
  white-space: nowrap;
}
.welcome-copy {
  position: absolute;
  top: 0;
  left: 100%;
}
.welcome-item strong {
  font-weight: 650;
  color: var(--accent);
}
.welcome-close {
  display: grid;
  place-items: center;
  flex: none;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0.7;
}
.welcome-close:hover {
  opacity: 1;
  background: color-mix(in srgb, var(--accent) 12%, transparent);
}
@keyframes welcome-scroll {
  to {
    transform: translateX(-100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .welcome-track {
    animation: none;
  }
  .welcome-copy {
    display: none;
  }
}
</style>
