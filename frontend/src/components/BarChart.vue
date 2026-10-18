<template>
  <div class="chart" :style="{ height: `${height}px` }">
    <div class="chart-y" :style="{ width: `${axisWidth}px` }">
      <span v-for="t in ticks" :key="t" :style="{ bottom: `${(t / top) * 100}%` }">{{ axisFormat(t) }}</span>
    </div>
    <div class="chart-plot" @mouseleave="hover = -1">
      <div v-for="t in ticks" :key="`g${t}`" class="chart-grid" :style="{ bottom: `${(t / top) * 100}%` }" />
      <div class="chart-cols">
        <div
          v-for="(row, i) in data"
          :key="i"
          class="chart-col"
          :class="{ active: hover === i }"
          @mouseenter="hover = i"
          @click="hover = i"
        >
          <div class="chart-bars">
            <div
              v-for="s in series"
              :key="s.key"
              class="chart-bar"
              :style="{ height: barHeight(row[s.key]), background: s.color }"
            />
          </div>
        </div>
      </div>
      <div v-if="isEmpty" class="chart-empty">{{ emptyText }}</div>
      <div v-if="hover >= 0 && data[hover] && !isEmpty" class="chart-tip" :style="tipStyle">
        <div class="chart-tip-title">{{ labelFormat(data[hover][xKey], true) }}</div>
        <div v-for="s in series" :key="s.key" class="chart-tip-row">
          <i :style="{ background: s.color }" />
          <span>{{ s.label }}</span>
          <b>{{ (s.format || format)(data[hover][s.key]) }}</b>
        </div>
      </div>
    </div>
    <div class="chart-x">
      <span v-for="(row, i) in data" :key="i" :class="{ show: showLabel(i) }">{{ labelFormat(row[xKey]) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  series: { type: Array, required: true }, // [{ key, label, color, format? }]
  xKey: { type: String, default: 'date' },
  height: { type: Number, default: 240 },
  format: { type: Function, default: (v) => String(v) },
  axisFormat: { type: Function, default: (v) => String(v) },
  labelFormat: { type: Function, default: (v) => String(v) },
  integer: Boolean,
  axisWidth: { type: Number, default: 56 },
  emptyText: { type: String, default: '这段时间还没有数据' },
})

const hover = ref(-1)
const isEmpty = computed(() =>
  props.data.every((row) => props.series.every((s) => !(Number(row[s.key]) > 0))),
)

function niceStep(raw) {
  if (raw <= 0) return 1
  const exp = Math.pow(10, Math.floor(Math.log10(raw)))
  const f = raw / exp
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10
  return nice * exp
}

const top = computed(() => {
  let max = 0
  for (const row of props.data) for (const s of props.series) max = Math.max(max, Number(row[s.key]) || 0)
  let step = niceStep(max / 4)
  if (props.integer) step = Math.max(1, Math.ceil(step))
  return step * 4
})
const ticks = computed(() => [0, 1, 2, 3, 4].map((i) => (top.value / 4) * i))

function barHeight(value) {
  const v = Number(value) || 0
  if (v <= 0) return '0'
  return `max(2px, ${(v / top.value) * 100}%)`
}

// Count back from the newest point so the latest day is always labelled.
function showLabel(i) {
  const n = props.data.length
  const step = Math.max(1, Math.ceil(n / 8))
  return (n - 1 - i) % step === 0
}

const tipStyle = computed(() => {
  const n = props.data.length || 1
  const pos = ((hover.value + 0.5) / n) * 100
  const shift = pos < 22 ? '0%' : pos > 78 ? '-100%' : '-50%'
  return { left: `${pos}%`, transform: `translateX(${shift})` }
})
</script>

<style scoped>
.chart {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) 24px;
  padding-top: 10px;
  user-select: none;
}
.chart-y {
  position: relative;
  grid-row: 1;
  grid-column: 1;
}
.chart-y span {
  position: absolute;
  right: 10px;
  transform: translateY(50%);
  font-size: 11px;
  color: var(--faint);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.chart-plot {
  position: relative;
  grid-row: 1;
  grid-column: 2;
  border-bottom: 1px solid var(--border-strong);
}
.chart-grid {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px dashed var(--border);
}
.chart-cols {
  position: absolute;
  inset: 0;
  display: flex;
}
.chart-col {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: center;
  border-radius: 4px 4px 0 0;
  cursor: default;
}
.chart-col.active {
  background: color-mix(in srgb, var(--accent) 7%, transparent);
}
.chart-bars {
  width: 64%;
  max-width: 44px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 2px;
}
.chart-bar {
  flex: 1;
  min-width: 0;
  max-width: 22px;
  border-radius: 3px 3px 0 0;
  transition: height 0.35s ease;
}
.chart-x {
  grid-row: 2;
  grid-column: 2;
  display: flex;
}
.chart-x span {
  flex: 1;
  min-width: 0;
  padding-top: 6px;
  text-align: center;
  font-size: 11px;
  color: var(--faint);
  white-space: nowrap;
  visibility: hidden;
  overflow: visible;
}
.chart-x span.show {
  visibility: visible;
}
.chart-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--faint);
  font-size: 13px;
  pointer-events: none;
}
.chart-tip {
  position: absolute;
  top: 0;
  z-index: 2;
  min-width: 150px;
  padding: 9px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  box-shadow: var(--shadow-lg);
  pointer-events: none;
  font-size: 12.5px;
}
.chart-tip-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.chart-tip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
}
.chart-tip-row i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}
.chart-tip-row b {
  margin-left: auto;
  padding-left: 12px;
  color: var(--text);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
