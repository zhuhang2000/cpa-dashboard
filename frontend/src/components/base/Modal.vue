<template>
  <Teleport to="body">
    <!-- 打开时从触发按钮的位置放大，关闭时缩回该按钮；过渡样式见 styles/components/modal.css 的 .dialog-*。
         :duration 必须与 CSS 中面板的过渡时长一致: Vue 只监听蒙层自身的过渡，不写会提前结束、面板跳到终点。 -->
    <Transition
      name="dialog"
      appear
      :duration="{ enter: 420, leave: 300 }"
      @enter="placeAtOrigin"
      @leave="placeAtOrigin"
    >
      <div v-if="open" class="modal-overlay" @mousedown.self="onBackdrop">
        <div class="modal" :class="{ wide, xwide }" role="dialog" aria-modal="true" :aria-label="title">
          <div class="modal-header">
            <slot name="header">
              <div class="modal-title">{{ title }}</div>
            </slot>
            <button class="btn btn-ghost btn-icon btn-sm" type="button" aria-label="关闭" @click="emit('close')">
              <Icon name="x" :size="18" />
            </button>
          </div>
          <div class="modal-body"><slot /></div>
          <div v-if="$slots.footer" class="modal-footer"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
// 所有 Modal 共用一个监听: 记录最近一次按下的按钮，作为弹窗放大 / 缩回的起点。
// 位置在按下时就记下来，按钮随后被移除 (如下拉菜单项) 也不影响；用捕获阶段，不会被 stopPropagation 拦掉。
let lastPress = null
document.addEventListener(
  'pointerdown',
  (e) => {
    const el = e.target instanceof Element ? e.target.closest('button, a, [role="button"]') : null
    lastPress = el && { el, rect: el.getBoundingClientRect(), at: performance.now() }
  },
  true,
)
</script>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import Icon from './Icon.vue'

// 按下按钮后这段时间内打开的弹窗才算由它触发；超时 (如接口返回后才弹出、键盘操作) 则从正中弹出。
const TRIGGER_WINDOW_MS = 1000
// 起始缩放的下限，避免从很小的图标按钮里像针尖一样放大。
const MIN_SCALE = 0.2

const props = defineProps({
  open: Boolean,
  title: { type: String, default: '' },
  wide: Boolean,
  xwide: Boolean,
  persistent: Boolean,
})
const emit = defineEmits(['close'])

// 本次打开的触发按钮 ({ el, rect })，没有则为 null。
let origin = null

function onKey(e) {
  if (e.key === 'Escape' && !props.persistent) emit('close')
}
function onBackdrop() {
  if (!props.persistent) emit('close')
}

// 触发按钮当前的位置: 按钮还在页面上就重新取 (弹窗打开期间页面可能滚动过)，否则用按下时记下的位置。
function triggerRect() {
  if (!origin) return null
  const live = origin.el.isConnected && origin.el.getBoundingClientRect()
  return live && live.width && live.height ? live : origin.rect
}

// 打开和关闭时各调用一次: 把触发按钮相对面板的位移与缩放写进 --from-*，
// 供 .dialog-enter-from / .dialog-leave-to 使用。没有触发按钮时不写，CSS 缺省值让面板从正中轻微放大。
function placeAtOrigin(overlay) {
  const panel = overlay.querySelector('.modal')
  const r = triggerRect()
  if (!panel || !r) return
  // offset* 不受 transform 影响，动画进行中也能量到面板的最终位置；蒙层铺满视口，所以就是视口坐标。
  const w = panel.offsetWidth
  const h = panel.offsetHeight
  // 宽高用同一个缩放比例，避免面板里的文字在动画中被压扁。
  const scale = Math.max(r.width / w, r.height / h, MIN_SCALE)
  // 写变量时先关掉过渡。打开时 enter-from 与 enter-active 已同时生效，上面量尺寸时浏览器已按 CSS 缺省起点
  // (正中、略缩小) 算过一次样式；这时直接改变量会被当成一次样式变化，面板先朝按钮“过渡”，下一帧 enter-from
  // 移除后又折返正中，看起来就没有从按钮飞出。关掉过渡写入、强制重算样式后再恢复，起点就直接落在按钮上。
  panel.style.transition = 'none'
  panel.style.setProperty('--from-x', `${r.left + r.width / 2 - (panel.offsetLeft + w / 2)}px`)
  panel.style.setProperty('--from-y', `${r.top + r.height / 2 - (panel.offsetTop + h / 2)}px`)
  panel.style.setProperty('--from-s', scale.toFixed(3))
  void panel.offsetWidth
  panel.style.transition = ''
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      origin = lastPress && performance.now() - lastPress.at < TRIGGER_WINDOW_MS ? lastPress : null
      document.addEventListener('keydown', onKey)
    } else document.removeEventListener('keydown', onKey)
  },
  { immediate: true },
)
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>
