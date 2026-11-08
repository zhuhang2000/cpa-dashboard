<template>
  <div class="trend">
    <div class="trend-head">
      <span>近 7 天消耗</span>
      <b class="num">{{ summary ? money(summary.range.cost) : '—' }}</b>
    </div>
    <div v-if="failed" class="trend-plot trend-note">加载失败</div>
    <div v-else-if="!summary" class="trend-plot skeleton" />
    <div
      v-else
      ref="plot"
      class="trend-plot"
      role="img"
      tabindex="0"
      :aria-label="ariaLabel"
      @pointerdown="onPointer"
      @pointermove="onPointer"
      @pointerleave="active = -1"
      @focus="active = points.length - 1"
      @blur="active = -1"
      @keydown.left.prevent="step(-1)"
      @keydown.right.prevent="step(1)"
    >
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient :id="fillId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" class="fill-top" />
            <stop offset="1" class="fill-bottom" />
          </linearGradient>
        </defs>
        <path :d="`${line}L100,100L0,100Z`" :fill="`url(#${fillId})`" />
        <path :d="line" class="trend-line" />
      </svg>
      <div v-if="active >= 0" class="trend-cross" :style="{ left: `${points[active].x}%` }" />
      <span class="trend-dot" :style="{ left: `${dot.x}%`, top: `${dot.y}%` }" />
      <div v-if="active >= 0" class="trend-tip" :style="tipStyle">
        <b class="num">{{ money(daily[active].cost) }}</b>
        <span>{{ dayName(active) }}</span>
      </div>
      <div v-if="isEmpty" class="trend-note">近 7 天暂无消耗</div>
    </div>
    <div class="trend-x">
      <span>{{ daily.length ? dayLabel(daily[0].date) : '' }}</span
      ><span>今天</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, useId } from 'vue'
import { usageApi } from '@/api/usage'
import { dayLabel, money } from '@/utils/format'

// Daily API spend for the last 7 days (oldest first, ending today), drawn as a single smoothed line.
const DAYS = 7
const summary = ref(null)
const failed = ref(false)
const active = ref(-1)
const plot = ref(null)
const fillId = `spend-fill-${useId()}`

const daily = computed(() => summary.value?.daily || [])
const isEmpty = computed(() => daily.value.every((d) => !(Number(d.cost) > 0)))

// Plot space is a 0–100 box stretched over the element; 14% headroom keeps the peak off the top edge.
const points = computed(() => {
  const values = daily.value.map((d) => Number(d.cost) || 0)
  const max = Math.max(...values, 0)
  const last = Math.max(values.length - 1, 1)
  return values.map((v, i) => ({ x: (i / last) * 100, y: max > 0 ? 100 - (v / max) * 86 : 100 }))
})
const line = computed(() => monotonePath(points.value))
const dot = computed(() => points.value[active.value >= 0 ? active.value : points.value.length - 1])

// Above the point unless that would cover the header; end points align inward so the tip stays in the card.
const tipStyle = computed(() => {
  const i = active.value
  const p = points.value[i]
  const tx = i === 0 ? '-12px' : i === points.value.length - 1 ? 'calc(-100% + 12px)' : '-50%'
  const ty = p.y < 45 ? '12px' : 'calc(-100% - 12px)'
  return { left: `${p.x}%`, top: `${p.y}%`, transform: `translate(${tx}, ${ty})` }
})

const ariaLabel = computed(
  () => `近 7 天每日消耗：${daily.value.map((d, i) => `${dayName(i)} ${money(d.cost)}`).join('，')}`,
)

function dayName(i) {
  return i === daily.value.length - 1 ? '今天' : dayLabel(daily.value[i].date)
}

function onPointer(e) {
  const rect = plot.value.getBoundingClientRect()
  const t = (e.clientX - rect.left) / rect.width
  const last = points.value.length - 1
  active.value = Math.min(last, Math.max(0, Math.round(t * last)))
}

function step(delta) {
  const last = points.value.length - 1
  active.value = Math.min(last, Math.max(0, (active.value < 0 ? last : active.value) + delta))
}

// Monotone cubic (Fritsch–Carlson): smooth, but never overshoots a data point, so a
// zero day stays on the baseline instead of dipping below it.
function monotonePath(pts) {
  if (pts.length < 2) return ''
  const n = pts.length
  const slope = []
  for (let i = 0; i < n - 1; i++) slope.push((pts[i + 1].y - pts[i].y) / (pts[i + 1].x - pts[i].x))
  const tangent = [slope[0]]
  for (let i = 1; i < n - 1; i++) {
    const [s0, s1] = [slope[i - 1], slope[i]]
    tangent.push(
      s0 * s1 <= 0 ? 0 : (Math.sign(s0) + Math.sign(s1)) * Math.min(Math.abs(s0), Math.abs(s1), Math.abs(s0 + s1) / 4),
    )
  }
  tangent.push(slope[n - 2])
  let d = `M${pts[0].x},${pts[0].y}`
  for (let i = 0; i < n - 1; i++) {
    const h = (pts[i + 1].x - pts[i].x) / 3
    d += `C${pts[i].x + h},${pts[i].y + tangent[i] * h} ${pts[i + 1].x - h},${pts[i + 1].y - tangent[i + 1] * h} ${pts[i + 1].x},${pts[i + 1].y}`
  }
  return d
}

onMounted(async () => {
  try {
    summary.value = await usageApi.usageSummary({ days: DAYS })
  } catch {
    failed.value = true
  }
})
</script>

<style scoped>
.trend {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.trend-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 100px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
}
.trend-head b {
  color: var(--text);
  font-size: 15px;
  font-weight: 600;
}
.trend-plot {
  position: relative;
  flex: 1;
  min-height: 88px;
  margin-top: 12px;
  border-bottom: 1px solid var(--border);
  touch-action: pan-y;
}
.trend-plot:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
  border-radius: 2px;
}
.trend-plot svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.fill-top {
  stop-color: var(--chart-1);
  stop-opacity: 0.16;
}
.fill-bottom {
  stop-color: var(--chart-1);
  stop-opacity: 0.02;
}
.trend-line {
  fill: none;
  stroke: var(--chart-1);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
.trend-cross {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--border-strong);
  transform: translateX(-0.5px);
  pointer-events: none;
}
/* Today by default, the hovered day otherwise; the surface ring keeps it clear of the line. */
.trend-dot {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--chart-1);
  box-shadow: 0 0 0 2px var(--surface);
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.trend-tip {
  position: absolute;
  z-index: 1;
  display: flex;
  flex-direction: column;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  box-shadow: var(--shadow);
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
  white-space: nowrap;
  pointer-events: none;
}
.trend-tip b {
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}
.trend-note {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 12px;
}
.trend-plot.trend-note {
  position: relative;
}
.trend-x {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  color: var(--muted);
  font-size: 11px;
}
</style>
