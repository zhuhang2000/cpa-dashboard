<template>
  <svg
    viewBox="0 0 560 410"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    aria-label="一个 API 密钥同时接入 OpenAI、Claude 与 Gemini"
  >
    <defs>
      <linearGradient id="auth-art-brand" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#4f5bd5" />
        <stop offset="1" stop-color="#8b5cf6" />
      </linearGradient>
      <!-- userSpaceOnUse: the straight middle wire has a zero-height bbox -->
      <linearGradient id="auth-art-wire" gradientUnits="userSpaceOnUse" x1="236" y1="0" x2="372" y2="0">
        <stop offset="0" stop-color="#4f5bd5" />
        <stop offset="1" stop-color="#a78bfa" />
      </linearGradient>
      <radialGradient id="auth-art-glow">
        <stop offset="0" stop-color="#6366f1" stop-opacity="0.16" />
        <stop offset="1" stop-color="#6366f1" stop-opacity="0" />
      </radialGradient>
      <filter id="auth-art-shadow" x="-30%" y="-30%" width="160%" height="190%">
        <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#312e81" flood-opacity="0.09" />
      </filter>
    </defs>

    <circle cx="130" cy="200" r="130" fill="url(#auth-art-glow)" />

    <!-- one key fans out to every upstream -->
    <g fill="none" stroke-width="2" stroke-linecap="round">
      <path v-for="m in models" :key="m.name" :d="wire(m.y)" stroke="#dde1f7" />
      <path v-for="m in models" :key="`${m.name}-flow`" :d="wire(m.y)" stroke="url(#auth-art-wire)" class="art-flow" />
    </g>

    <g v-for="m in models" :key="m.name">
      <rect
        x="372"
        :y="m.y - 26"
        width="164"
        height="52"
        rx="14"
        fill="#fff"
        stroke="#e6e8f2"
        filter="url(#auth-art-shadow)"
      />
      <circle cx="400" :cy="m.y" r="15" :fill="m.soft" />
      <text
        x="400"
        :y="m.y"
        text-anchor="middle"
        dominant-baseline="central"
        font-size="14"
        font-weight="700"
        :fill="m.color"
      >
        {{ m.name[0] }}
      </text>
      <text x="426" :y="m.y" dominant-baseline="central" font-size="14" font-weight="600" fill="#111827">
        {{ m.name }}
      </text>
      <circle cx="512" :cy="m.y" r="8" fill="#e7f6ed" />
      <path
        :d="`M508.5 ${m.y} l2.5 2.5 4.5-5`"
        fill="none"
        stroke="#138a4a"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <circle cx="372" :cy="m.y" r="4.5" fill="#fff" stroke="#a78bfa" stroke-width="2" />
    </g>

    <!-- the key -->
    <rect x="24" y="146" width="212" height="108" rx="16" fill="#fff" stroke="#e6e8f2" filter="url(#auth-art-shadow)" />
    <rect x="44" y="166" width="40" height="40" rx="11" fill="url(#auth-art-brand)" />
    <g
      transform="translate(52 174)"
      fill="none"
      stroke="#fff"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <circle cx="7.5" cy="15.5" r="5.5" />
      <path d="m21 2-9.6 9.6" />
      <path d="m15.5 7.5 3 3L22 7l-3-3" />
    </g>
    <text x="96" y="178" dominant-baseline="central" font-size="12" fill="#6b7280">API 密钥</text>
    <rect x="180" y="169" width="36" height="18" rx="9" fill="#e7f6ed" />
    <text
      x="198"
      y="178"
      text-anchor="middle"
      dominant-baseline="central"
      font-size="11"
      font-weight="600"
      fill="#138a4a"
    >
      启用
    </text>
    <text x="96" y="198" dominant-baseline="central" font-size="13" fill="#111827" class="art-mono">sk-••••••3f9a</text>
    <rect x="44" y="228" width="172" height="6" rx="3" fill="#eceef3" />
    <rect x="44" y="228" width="62" height="6" rx="3" fill="url(#auth-art-brand)" />
    <circle cx="236" cy="200" r="5" fill="#fff" stroke="#4f5bd5" stroke-width="2" />

    <g class="art-float">
      <rect x="64" y="52" width="168" height="52" rx="14" fill="#fff" stroke="#e6e8f2" filter="url(#auth-art-shadow)" />
      <circle cx="90" cy="78" r="13" fill="#e7f6ed" />
      <path d="M90 72v12M84 78h12" stroke="#138a4a" stroke-width="2" stroke-linecap="round" />
      <text x="112" y="69" dominant-baseline="central" font-size="11.5" fill="#6b7280">充值到账</text>
      <text x="112" y="88" dominant-baseline="central" font-size="14" font-weight="700" fill="#138a4a">
        {{ money(50, { sign: true }) }}
      </text>
    </g>

    <g class="art-float art-float-late">
      <rect
        x="56"
        y="286"
        width="236"
        height="92"
        rx="16"
        fill="#fff"
        stroke="#e6e8f2"
        filter="url(#auth-art-shadow)"
      />
      <text x="78" y="312" dominant-baseline="central" font-size="12" fill="#6b7280">本月消费</text>
      <text x="78" y="341" dominant-baseline="central" font-size="20" font-weight="700" fill="#111827">
        {{ money(36.2) }}
      </text>
      <rect
        v-for="(h, i) in bars"
        :key="i"
        :x="190 + i * 12"
        :y="358 - h"
        width="8"
        :height="h"
        rx="2.5"
        :fill="i === bars.length - 1 ? 'url(#auth-art-brand)' : '#dfe3fb'"
      />
    </g>
  </svg>
</template>

<script setup>
import { money } from '@/utils/format'

// Decorative only; brand colours approximate each vendor, no logos.
const models = [
  { name: 'OpenAI', color: '#10a37f', soft: '#e3f5ef', y: 86 },
  { name: 'Claude', color: '#d97757', soft: '#fbebe5', y: 200 },
  { name: 'Gemini', color: '#4b7bec', soft: '#e6edfd', y: 314 },
]
const bars = [18, 28, 22, 34, 26, 38, 46]

function wire(y) {
  return `M236 200 C300 200 306 ${y} 372 ${y}`
}
</script>

<style scoped>
.art-mono {
  font-family: var(--mono);
}
.art-flow {
  stroke-dasharray: 6 8;
  animation: art-flow 1.4s linear infinite;
}
.art-float {
  animation: art-float 6s ease-in-out infinite;
}
.art-float-late {
  animation-delay: -3s;
}
@keyframes art-flow {
  to {
    stroke-dashoffset: -28;
  }
}
@keyframes art-float {
  50% {
    transform: translateY(-6px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .art-flow,
  .art-float {
    animation: none;
  }
}
</style>
