<template>
  <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>时间</th>
          <th>密钥</th>
          <th>模型</th>
          <th class="right">输入</th>
          <th class="right">输出</th>
          <th class="right">费用</th>
          <th>状态 / 耗时</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in items" :key="r.id">
          <td class="nowrap num" :title="dateTime(r.ts, { seconds: true })">{{ shortTime(r.ts) }}</td>
          <td class="nowrap">{{ r.key_name }}</td>
          <td>
            <div class="mono nowrap">{{ r.model }}</div>
            <div v-if="r.endpoint" class="cell-sub mono">{{ r.endpoint }}</div>
          </td>
          <td class="right num nowrap" :title="inputTitle(r)">
            {{ tokens(r.input_tokens + r.cache_read_tokens + r.cache_write_tokens) }}
            <div v-if="r.cache_read_tokens || r.cache_write_tokens" class="cell-sub">
              缓存 {{ tokens(r.cache_read_tokens + r.cache_write_tokens) }}
            </div>
          </td>
          <td class="right num nowrap" :title="r.reasoning_tokens ? `其中推理 ${num(r.reasoning_tokens)}` : ''">
            {{ tokens(r.output_tokens) }}
            <div v-if="r.reasoning_tokens" class="cell-sub">推理 {{ tokens(r.reasoning_tokens) }}</div>
          </td>
          <td class="right num nowrap">
            <b>{{ money(r.cost) }}</b>
          </td>
          <td class="nowrap">
            <span class="badge" :class="r.failed ? 'badge-danger' : 'badge-success'">{{
              r.failed ? '失败' : '成功'
            }}</span>
            <div class="cell-sub num">
              {{ duration(r.latency_ms)
              }}<template v-if="r.stream !== null"> · {{ r.stream ? '流式' : '非流式' }}</template>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { dateTime, duration, money, num, tokens } from '@/utils/format'

// One page of usage records, shared by the usage page and the admin user detail.
defineProps({
  items: { type: Array, required: true },
})

function shortTime(ms) {
  const full = dateTime(ms, { seconds: true })
  return new Date(ms).getFullYear() === new Date().getFullYear() ? full.slice(5) : full
}

function inputTitle(r) {
  return `未缓存 ${num(r.input_tokens)} · 缓存读取 ${num(r.cache_read_tokens)} · 缓存写入 ${num(r.cache_write_tokens)}`
}
</script>
