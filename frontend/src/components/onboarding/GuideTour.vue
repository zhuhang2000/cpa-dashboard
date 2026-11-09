<template>
  <button
    ref="trigger"
    class="btn guide-btn"
    :class="nudge ? 'nudge' : 'btn-ghost btn-icon'"
    aria-label="新手引导"
    aria-haspopup="dialog"
    @click="start"
  >
    <Icon name="help" />
    <template v-if="nudge">
      <span class="guide-label">新手引导</span>
      <span class="guide-dot" />
    </template>
  </button>

  <Teleport to="body">
    <div v-if="open" class="guide" role="dialog" aria-modal="true" :aria-label="step.title">
      <div
        ref="spotEl"
        class="guide-spot"
        :class="{ empty: !spot.w }"
        :style="{ left: `${spot.x}px`, top: `${spot.y}px`, width: `${spot.w}px`, height: `${spot.h}px` }"
      />
      <div
        ref="bubble"
        class="guide-bubble"
        :class="{ shown: !gliding }"
        :style="{ left: `${pos.left}px`, top: `${pos.top}px` }"
        aria-live="polite"
      >
        <div class="guide-count">{{ index + 1 }} / {{ steps.length }}</div>
        <div class="guide-title">{{ step.title }}</div>
        <p class="guide-body">{{ step.body }}</p>
        <p v-if="step.tip" class="guide-tip"><Icon name="coins" :size="15" />{{ step.tip }}</p>
        <div class="guide-actions">
          <button v-if="!isLast" class="btn btn-ghost btn-sm guide-skip" @click="close">跳过</button>
          <button v-if="index > 0" class="btn btn-sm" @click="go(index - 1)">上一步</button>
          <button ref="nextBtn" class="btn btn-primary btn-sm" @click="isLast ? close() : go(index + 1)">
            {{ index === 0 ? '开始' : isLast ? '完成' : '下一步' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '@/components/base/Icon.vue'
import { siteStore, sessionStore } from '@/stores'

// The guide only opens from this top-bar button, never by itself. While the user has no API keys the button is a
// labelled badge with a red dot, so it is hard to miss. Closing the guide flies it back into the button.
// Space around the highlighted element, between it and the bubble, and between the bubble and the window edges.
const PAD = 6
const GAP = 12
const EDGE = 16
// How long the spotlight takes to move to the next element, and the bubble to fly into the button.
const GLIDE_MS = 420
const FLY_MS = 500
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const route = useRoute()
const router = useRouter()

// A step highlights the element whose data-tour attribute is its `target` (none: the bubble is centred),
// and puts the bubble on its preferred `side` when there is room, else the first side that has it.
const steps = computed(() => [
  {
    title: `欢迎来到 ${siteStore.siteName} 👋`,
    body: '只需三步即可开始调用：充值、创建密钥、配置 Codex。花 30 秒带你认识一下控制台。',
  },
  {
    target: 'balance',
    title: '第一步：充值',
    body:
      '调用按实际用量从余额扣费，余额为 0 时密钥无法调用。本站价格与官方一致，充 1 元当 1 美元花。' +
      (siteStore.status?.payment?.online ? '点「充值」可用兑换码或在线支付。' : '点「充值」可用兑换码充值。'),
  },
  {
    target: 'key',
    title: '第二步：创建 API 密钥',
    body: '密钥是你调用接口的凭证，等同于账户余额，请勿泄露或提交到公开仓库。',
  },
  {
    target: 'connect',
    title: '第三步：配置 Codex',
    body: '推荐用「Cockpit Tools」配置 Codex「接入地址」和「API 密钥」；第一次接触 Codex 可以先看「Codex 介绍」。',
  },
  {
    target: 'usage',
    title: '查看用量',
    body: '开始调用后，这里和上方的「消费趋势」会显示每天的花费和各模型的消费。点「查看明细」可以看每一次请求。',
  },
  {
    target: 'contact',
    side: 'left',
    title: '有问题随时找我们',
    body: '需要兑换码、充值遇到问题或不会配置，点这里扫码加管理员微信。',
    tip: '新用户联系管理员可领20$体验金',
  },
])

const open = ref(false)
const index = ref(0)
const step = computed(() => steps.value[index.value])
const isLast = computed(() => index.value === steps.value.length - 1)
const trigger = ref(null)
const spotEl = ref(null)
const bubble = ref(null)
const nextBtn = ref(null)
const nudge = computed(() => sessionStore.keyCount === 0)
// Where the spotlight and the bubble are drawn, in window coordinates.
const spot = reactive({ x: 0, y: 0, w: 0, h: 0 })
const pos = reactive({ left: 0, top: 0 })
// The bubble is hidden while the spotlight glides to the next element, so it doesn't jump about.
const gliding = ref(false)
let glide = null
let frame = 0
let leaving = false

watch(open, (isOpen, _, onCleanup) => {
  if (!isOpen) return
  frame = requestAnimationFrame(tick)
  document.addEventListener('keydown', onKey)
  nextTick(() => nextBtn.value?.focus())
  onCleanup(() => {
    cancelAnimationFrame(frame)
    document.removeEventListener('keydown', onKey)
  })
})

// It only explains the overview page, so it closes when the page is left.
watch(
  () => route.path,
  (path) => {
    if (path !== '/') close()
  },
)

function start() {
  if (leaving) return
  if (route.path !== '/') router.push('/')
  index.value = 0
  glide = null
  gliding.value = false
  open.value = true
}

function go(i) {
  index.value = i
  if (!reduceMotion) {
    glide = { from: { ...spot } }
    gliding.value = true
  }
  // Scroll the element to the middle unless it is already in view below the sticky top bar.
  const el = target()
  const r = el?.getBoundingClientRect()
  const topBar = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--topbar-h'))
  if (r && (r.top < topBar || r.bottom > document.documentElement.clientHeight)) {
    el.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' })
  }
}

// Finishing, skipping or leaving the page flies the guide into the top-bar button.
async function close() {
  if (!open.value || leaving) return
  leaving = true
  cancelAnimationFrame(frame)
  const from = bubble.value.getBoundingClientRect()
  const to = trigger.value.getBoundingClientRect()
  const dx = to.left + to.width / 2 - (from.left + from.width / 2)
  const dy = to.top + to.height / 2 - (from.top + from.height / 2)
  const timing = { duration: reduceMotion ? 0 : FLY_MS, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', fill: 'forwards' }
  spotEl.value.animate([{ opacity: 1 }, { opacity: 0 }], timing)
  await bubble.value.animate(
    [
      { opacity: 1, transform: 'none' },
      { opacity: 0, transform: `translate(${dx}px, ${dy}px) scale(0.1)` },
    ],
    timing,
  ).finished
  leaving = false
  open.value = false
  trigger.value?.focus()
}

// While open, measure again every frame. This follows smooth scrolling, resizing and content that loads late
// without a listener for each.
function tick(now) {
  frame = requestAnimationFrame(tick)
  const rect = targetRect()
  if (glide) {
    glide.start ??= now
    const t = Math.min(1, (now - glide.start) / GLIDE_MS)
    const eased = 1 - (1 - t) ** 3
    for (const k in rect) rect[k] = glide.from[k] + (rect[k] - glide.from[k]) * eased
    if (t === 1) {
      glide = null
      gliding.value = false
    }
  }
  Object.assign(spot, rect)
  if (!gliding.value && bubble.value) placeBubble()
}

function target() {
  return step.value.target ? document.querySelector(`[data-tour="${step.value.target}"]`) : null
}

function targetRect() {
  const r = target()?.getBoundingClientRect()
  // No element (the welcome step): an empty spotlight in the middle, so the whole page is dimmed.
  if (!r?.width) {
    const { clientWidth, clientHeight } = document.documentElement
    return { x: clientWidth / 2, y: clientHeight / 2, w: 0, h: 0 }
  }
  return { x: r.left - PAD, y: r.top - PAD, w: r.width + PAD * 2, h: r.height + PAD * 2 }
}

function placeBubble() {
  const { clientWidth: vw, clientHeight: vh } = document.documentElement
  const { offsetWidth: w, offsetHeight: h } = bubble.value
  let left = spot.x + (spot.w - w) / 2
  let top = spot.y + (spot.h - h) / 2
  if (spot.w) {
    const room = {
      bottom: vh - EDGE - (spot.y + spot.h + GAP) >= h,
      top: spot.y - GAP - EDGE >= h,
      left: spot.x - GAP - EDGE >= w,
      right: vw - EDGE - (spot.x + spot.w + GAP) >= w,
    }
    const side = [step.value.side, 'bottom', 'top', 'left', 'right'].find((s) => room[s])
    if (side === 'bottom') top = spot.y + spot.h + GAP
    else if (side === 'top') top = spot.y - GAP - h
    else if (side === 'left') left = spot.x - GAP - w
    else if (side === 'right') left = spot.x + spot.w + GAP
    // No room beside it (a tall card on a phone): at the bottom of the window, over the element.
    else top = vh - EDGE - h
  }
  pos.left = Math.min(Math.max(left, EDGE), vw - EDGE - w)
  pos.top = Math.min(Math.max(top, EDGE), vh - EDGE - h)
}

function onKey(e) {
  if (e.key === 'Escape') close()
  else if (e.key === 'ArrowRight' && !isLast.value) go(index.value + 1)
  else if (e.key === 'ArrowLeft' && index.value > 0) go(index.value - 1)
}
</script>

<style scoped>
/* The badge for users without keys: an accent pill the height of the balance pill beside it. */
.guide-btn.nudge {
  --btn-color: var(--accent-text);
  --btn-bg: var(--accent-soft);
  --btn-border: color-mix(in srgb, var(--accent) 45%, transparent);
  --btn-shadow: none;
  --btn-hover-bg: color-mix(in srgb, var(--accent) 20%, var(--surface));
  --btn-hover-border: var(--accent);
  --btn-active-bg: color-mix(in srgb, var(--accent) 28%, var(--surface));
  position: relative;
  height: 34px;
  padding: 0 12px 0 10px;
  border-radius: 999px;
  font-weight: 600;
}
/* A dot on the corner with a ripple, like an unread notice. */
.guide-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--danger);
  box-shadow: 0 0 0 2px var(--bg);
}
/* On a narrow top bar only the icon and the dot are left. */
@media (max-width: 860px) {
  .guide-btn.nudge {
    width: 34px;
    padding: 0;
  }
  .guide-label {
    display: none;
  }
}
.guide {
  position: fixed;
  inset: 0;
  z-index: 100;
}
/* A hole over the highlighted element: its shadow dims everything else and rings the edge. The radius
   follows a card's corners, PAD outside them. */
.guide-spot {
  position: absolute;
  border-radius: calc(var(--radius) + 6px);
  box-shadow:
    0 0 0 2px var(--accent),
    0 0 0 9999px rgba(10, 12, 18, 0.55);
}
.guide-spot::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
}
.guide-spot.empty {
  box-shadow: 0 0 0 9999px rgba(10, 12, 18, 0.55);
}
.guide-spot.empty::after {
  display: none;
}
.guide-bubble {
  position: absolute;
  width: min(320px, calc(100vw - 32px));
  padding: 16px 18px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow-lg);
  opacity: 0;
  pointer-events: none;
}
.guide-bubble.shown {
  opacity: 1;
  pointer-events: auto;
  animation: pop-in 0.23s ease-out;
}
.guide-count {
  color: var(--faint);
  font-size: 12px;
}
.guide-title {
  margin-top: 2px;
  font-size: 15px;
  font-weight: 600;
}
.guide-body {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 13.5px;
}
.guide-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 10px 0 0;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 13px;
  font-weight: 500;
}
.guide-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}
/* Skip stays on the left, apart from back and next. */
.guide-skip {
  margin-right: auto;
}
</style>
