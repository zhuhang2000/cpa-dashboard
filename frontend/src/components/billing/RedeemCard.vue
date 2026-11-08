<template>
  <div class="card redeem-card">
    <form class="pane" @submit.prevent="redeem">
      <div class="redeem-title">
        <div class="card-title">兑换码充值</div>
        <span class="badge badge-accent plain"
          ><Icon name="coins" :size="13" />充 ¥100 到账 {{ currency() }}{{ num(100 * ratio) }}</span
        >
      </div>
      <div class="redeem-row">
        <input
          v-model.trim="code"
          class="input mono"
          aria-label="兑换码"
          placeholder="XXXX-XXXX-XXXX-XXXX"
          autocomplete="off"
          spellcheck="false"
          style="letter-spacing: 0.06em; text-transform: uppercase"
        />
        <button class="btn btn-primary" :disabled="redeeming || !code">
          <Icon v-if="redeeming" name="loader" :size="16" />
          {{ redeeming ? '兑换中…' : '立即兑换' }}
        </button>
      </div>
    </form>
    <div class="pane help">
      <button
        type="button"
        class="bubble"
        aria-haspopup="dialog"
        :aria-expanded="contactAdmin.open"
        @click="contactAdmin.toggle"
      >
        <span class="bubble-tab">
          <svg viewBox="0 0 5 5" width="15" height="15" shape-rendering="crispEdges" aria-hidden="true">
            <path fill="#6b4f3a" d="M0 4h1v1H0zM1 3h1v1H1z" />
            <path fill="#e8b84a" d="M3 0h1v1H3zM2 1h1v1H2zM4 1h1v1H4zM3 2h1v1H3z" />
            <path fill="#fff3c4" d="M3 1h1v1H3z" />
          </svg>
          小提示
        </span>
        <svg
          class="bubble-icon"
          viewBox="0 0 12 14"
          width="36"
          height="42"
          shape-rendering="crispEdges"
          aria-hidden="true"
        >
          <path fill="#2b2633" d="M2 1h8v1H2zM1 2h1v10H1zM10 2h1v1h-1zM11 3h1v9h-1zM2 12h9v1H2z" />
          <path fill="#4a3d55" d="M2 2h1v10H2z" />
          <path fill="#6a5878" d="M3 2h7v9H3z" />
          <path fill="#efe4c6" d="M10 3h1v9h-1zM3 11h7v1H3z" />
          <path fill="#d0aa55" d="M8 2h2v1H8zM9 3h1v1H9zM9 9h1v1H9zM8 10h2v1H8z" />
          <path fill="#c8473c" d="M4 11h1v3H4z" />
          <path fill="#62d0f5" d="M5 3h3v1H5zM4 4h1v1H4zM8 4h1v2H8zM6 6h2v1H6zM6 7h1v1H6zM6 9h1v1H6z" />
          <path class="spark-a" fill="#a6e6fb" d="M0 4h1v1H0zM11 0h1v1h-1z" />
          <path class="spark-b" fill="#a6e6fb" d="M0 9h1v1H0z" />
        </svg>
        <span class="bubble-text"><b>还没有兑换码？</b>点我联系管理员，有问必答</span>
        <svg
          class="bubble-next"
          viewBox="0 0 5 3"
          width="15"
          height="9"
          shape-rendering="crispEdges"
          aria-hidden="true"
        >
          <path d="M0 0h5v1H0zM1 1h3v1H1zM2 2h1v1H2z" />
        </svg>
      </button>
      <ClaudeArt class="claude-art" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import Icon from '@/components/base/Icon.vue'
import ClaudeArt from './ClaudeArt.vue'
import { contactAdmin } from '@/components/support/ContactAdmin.vue'
import { billingApi } from '@/api/billing'
import { siteStore } from '@/stores'
import { currency, money, num } from '@/utils/format'
import { toast } from '@/toast'

const emit = defineEmits(['redeemed'])
// Codes are sold at the same rate as online pay: ¥1 buys credit_ratio units of credit.
const ratio = computed(() => Number(siteStore.status?.payment?.credit_ratio) || 1)
const code = ref('')
const redeeming = ref(false)

async function redeem() {
  redeeming.value = true
  try {
    const data = await billingApi.redeem({ code: code.value })
    toast.success(`兑换成功，到账 ${money(data.amount)}`)
    code.value = ''
    emit('redeemed')
  } catch (e) {
    toast.error(e.message)
  } finally {
    redeeming.value = false
  }
}
</script>

<style scoped>
/* Code entry on top, where to get one below. When the row stretches the card (a taller balance card beside
   it), the help pane takes the extra height and keeps its content centred. */
.redeem-card {
  display: flex;
  flex-direction: column;
  container-type: inline-size;
}
.pane {
  padding: 20px 24px;
}
.redeem-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
}
/* No visible field label: the card title already names it and the placeholder shows the format. */
.redeem-row {
  margin-top: 14px;
  display: flex;
  gap: 8px;
}
.redeem-row .input {
  min-width: 0;
}
.redeem-row .btn {
  height: 38px;
}

/* Help row: the dialog bubble, which opens the app-wide contact-admin panel (it holds the WeChat QR), and the
   mascot "speaking" it from the right (it faces left). */
.pane.help {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  padding-block: 14px;
  border-top: 1px solid var(--border);
}
/* Transparent (switches sun/moon with the theme), 5:4 like its art, at 3px per art pixel: the bubble's grid.
   Its top and bottom rows are mostly sky, so they bleed into the pane padding and the bubble sets the row height. */
.claude-art {
  flex: none;
  width: 120px;
  height: 96px;
  margin: -6px 0;
}
/* Pixel dialog box on a --u grid, drawn as a raised pixel button: a 1-pixel ink outline with two-step rounded
   corners and a 1-pixel bevel inside it (light top/left, shade bottom/right), all background layers of the box;
   the speckled panel is ::before, inset by that 2-pixel frame. Colours are the art's palette, one set per theme. */
.bubble {
  --u: 3px;
  --u2: calc(var(--u) * 2);
  --u4: calc(var(--u) * 4);
  --ink: #2f2f2d;
  --hi: #eef2f6;
  --lo: #a9b5c2;
  --panel: #d3dbe3;
  --dot-hi: #e6ebf0;
  --dot-lo: #bcc6d0;
  --title: #2a2030;
  --title-shadow: #b3a6c2;
  --body: #3a3f4c;
  --tab: #e9dfc5;
  --tab-hi: #f7f0dc;
  --tab-lo: #cdbf9c;
  --tab-text: #2f2f2d;
  position: relative;
  isolation: isolate;
  /* Balances the tab sticking out above. */
  margin-top: var(--u2);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: calc(var(--u2) + 14px) calc(var(--u2) + 28px) calc(var(--u2) + 10px) calc(var(--u2) + 12px);
  border: 0;
  background:
    linear-gradient(var(--ink), var(--ink)) left var(--u) top var(--u) / var(--u) var(--u) no-repeat,
    linear-gradient(var(--ink), var(--ink)) right var(--u) top var(--u) / var(--u) var(--u) no-repeat,
    linear-gradient(var(--ink), var(--ink)) left var(--u) bottom var(--u) / var(--u) var(--u) no-repeat,
    linear-gradient(var(--ink), var(--ink)) right var(--u) bottom var(--u) / var(--u) var(--u) no-repeat,
    linear-gradient(var(--hi), var(--hi)) left var(--u2) top var(--u) / calc(100% - var(--u4)) var(--u) no-repeat,
    linear-gradient(var(--hi), var(--hi)) left var(--u) top var(--u2) / var(--u) calc(100% - var(--u4)) no-repeat,
    linear-gradient(var(--lo), var(--lo)) left var(--u2) bottom var(--u) / calc(100% - var(--u4)) var(--u) no-repeat,
    linear-gradient(var(--lo), var(--lo)) right var(--u) top var(--u2) / var(--u) calc(100% - var(--u4)) no-repeat,
    linear-gradient(var(--ink), var(--ink)) left var(--u2) top 0 / calc(100% - var(--u4)) var(--u) no-repeat,
    linear-gradient(var(--ink), var(--ink)) left var(--u2) bottom 0 / calc(100% - var(--u4)) var(--u) no-repeat,
    linear-gradient(var(--ink), var(--ink)) left 0 top var(--u2) / var(--u) calc(100% - var(--u4)) no-repeat,
    linear-gradient(var(--ink), var(--ink)) right 0 top var(--u2) / var(--u) calc(100% - var(--u4)) no-repeat;
  text-align: left;
  cursor: pointer;
}
.bubble:hover {
  --panel: #dee5ec;
}
.bubble:active {
  transform: translateY(2px);
}
:root[data-theme='dark'] .bubble {
  --ink: #4a4d57;
  --hi: #343c4f;
  --lo: #171b25;
  --panel: #232a38;
  --dot-hi: #2d3546;
  --dot-lo: #1b202b;
  --title: #f1ecf7;
  --title-shadow: #0a0b0f;
  --body: #b7bfce;
  --tab: #3b3528;
  --tab-hi: #4d4534;
  --tab-lo: #2a2519;
  --tab-text: #efe3c2;
}
:root[data-theme='dark'] .bubble:hover {
  --panel: #293142;
}
/* Panel: one-pixel speckles from three square-dot grids of different sizes, so they read as scattered. */
.bubble::before {
  content: '';
  position: absolute;
  inset: var(--u2);
  z-index: -1;
  background:
    conic-gradient(from 270deg at var(--u) var(--u), var(--dot-hi) 25%, transparent 0) 9px 6px / 57px 39px,
    conic-gradient(from 270deg at var(--u) var(--u), var(--dot-lo) 25%, transparent 0) 33px 24px / 69px 45px,
    conic-gradient(from 270deg at var(--u) var(--u), var(--dot-hi) 25%, transparent 0) 48px 30px / 81px 27px,
    var(--panel);
}
/* Tail toward the mascot, cut out of the frame itself: panel pixels open the shade and ink columns, and the
   ink outline steps out to a point. The pseudo-element is the root pixel on the ink column; each shadow adds
   one pixel:
     col  -1 0 1 2 3
     -3    ▒ █ · · ·      █ ink   ▒ shade   ░ panel
     -2    ░ ░ █ · ·
     -1    ░ ░ ░ █ ·
      0    ░ ░ ░ ░ █
      1    ░ ░ ░ █ ·
      2    ░ ░ █ · ·
      3    ▒ █ · · ·                                 */
.bubble::after {
  content: '';
  position: absolute;
  top: calc(50% - var(--u) / 2);
  left: calc(100% - var(--u));
  width: var(--u);
  height: var(--u);
  background: var(--panel);
  box-shadow:
    calc(var(--u) * -1) calc(var(--u) * -2) var(--panel),
    calc(var(--u) * -1) calc(var(--u) * -1) var(--panel),
    calc(var(--u) * -1) 0 var(--panel),
    calc(var(--u) * -1) var(--u) var(--panel),
    calc(var(--u) * -1) var(--u2) var(--panel),
    0 calc(var(--u) * -2) var(--panel),
    0 calc(var(--u) * -1) var(--panel),
    0 var(--u) var(--panel),
    0 var(--u2) var(--panel),
    var(--u) calc(var(--u) * -2) var(--ink),
    var(--u) calc(var(--u) * -1) var(--panel),
    var(--u) 0 var(--panel),
    var(--u) var(--u) var(--panel),
    var(--u) var(--u2) var(--ink),
    var(--u2) calc(var(--u) * -1) var(--ink),
    var(--u2) 0 var(--panel),
    var(--u2) var(--u) var(--ink),
    calc(var(--u) * 3) 0 var(--ink);
}
/* "小提示" tab riding the top frame: one-pixel notched ink outline, bevelled cream face. */
.bubble-tab {
  position: absolute;
  top: calc(var(--u) * -1);
  left: var(--u4);
  display: flex;
  align-items: center;
  gap: 4px;
  height: calc(var(--u) * 6);
  padding: 0 var(--u2);
  background: var(--tab);
  box-shadow:
    0 calc(var(--u) * -1) var(--ink),
    0 var(--u) var(--ink),
    calc(var(--u) * -1) 0 var(--ink),
    var(--u) 0 var(--ink),
    inset 0 var(--u) var(--tab-hi),
    inset 0 calc(var(--u) * -1) var(--tab-lo);
  color: var(--tab-text);
  font-size: 12px;
  font-weight: 600;
}
.bubble-text {
  color: var(--body);
  font-size: 13px;
  line-height: 1.5;
}
.bubble-text b {
  display: block;
  margin-bottom: 3px;
  color: var(--title);
  font-size: 15px;
  line-height: 1.35;
  text-shadow: 1px 1px 0 var(--title-shadow);
}
/* Blinking "more" cursor, bottom-right of the panel. */
.bubble-next {
  position: absolute;
  right: var(--u4);
  bottom: calc(var(--u) * 3);
  fill: var(--body);
  animation: bubble-next 1s steps(1) infinite;
}
.spark-a {
  animation: bubble-twinkle 1.6s steps(1) infinite;
}
.spark-b {
  animation: bubble-twinkle 1.6s steps(1) 0.8s infinite;
}
@keyframes bubble-next {
  50% {
    transform: translateY(var(--u));
  }
}
@keyframes bubble-twinkle {
  50% {
    opacity: 0.15;
  }
}
@media (prefers-reduced-motion: reduce) {
  .bubble-next,
  .spark-a,
  .spark-b {
    animation: none;
  }
}
/* Too narrow: drop the decorative mascot, the bubble's tail and its book. */
@container (max-width: 440px) {
  .claude-art,
  .bubble-icon,
  .bubble::after {
    display: none;
  }
}
@media (max-width: 560px) {
  .pane {
    padding: 16px;
  }
}
</style>
