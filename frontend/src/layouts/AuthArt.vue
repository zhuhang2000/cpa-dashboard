<template>
  <svg
    viewBox="36 0 496 384"
    preserveAspectRatio="xMinYMid meet"
    role="img"
    aria-label="订阅里的 Codex 被降智，晕头转向只会敷衍，又触发 5 小时限制；接上 AI 充电宝后满血接着写"
  >
    <defs>
      <linearGradient id="auth-art-brand" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#4f5bd5" />
        <stop offset="1" stop-color="#8b5cf6" />
      </linearGradient>
      <linearGradient id="auth-art-shine" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#fff" stop-opacity="0.26" />
        <stop offset="1" stop-color="#fff" stop-opacity="0" />
      </linearGradient>
      <!-- userSpaceOnUse so the colour runs along the cable, from the power bank to the phone -->
      <linearGradient id="auth-art-cable" gradientUnits="userSpaceOnUse" x1="298" y1="0" x2="142" y2="0">
        <stop offset="0" stop-color="#8b5cf6" />
        <stop offset="1" stop-color="#4f5bd5" />
      </linearGradient>
      <radialGradient id="auth-art-glow">
        <stop offset="0" stop-color="#6366f1" stop-opacity="0.16" />
        <stop offset="1" stop-color="#6366f1" stop-opacity="0" />
      </radialGradient>
      <filter id="auth-art-shadow" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#312e81" flood-opacity="0.09" />
      </filter>
      <filter id="auth-art-bank-shadow" x="-30%" y="-40%" width="160%" height="200%">
        <feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#4f46e5" flood-opacity="0.3" />
      </filter>
    </defs>

    <circle cx="142" cy="176" r="176" fill="url(#auth-art-glow)" />
    <circle cx="422" cy="192" r="130" fill="url(#auth-art-glow)" />

    <!-- the charging cable hangs between the power bank and the phone's bottom port -->
    <g fill="none" stroke-linecap="round">
      <path :d="cable" stroke="#dfe3fb" stroke-width="5" />
      <path :d="cable" stroke="url(#auth-art-cable)" stroke-width="2.2" class="art-flow" />
    </g>

    <!-- the phone: Codex on the subscription gets throttled and hits the limit, then carries on on API credit -->
    <rect x="40" y="10" width="204" height="320" rx="30" fill="#fff" stroke="#e6e8f2" filter="url(#auth-art-shadow)" />
    <rect x="48" y="18" width="188" height="304" rx="23" fill="#f7f8fc" />
    <rect x="120" y="25" width="44" height="13" rx="6.5" fill="#1f2333" />

    <text x="62" y="31.5" dominant-baseline="central" font-size="11" font-weight="600" fill="#111827">9:41</text>
    <path d="M192 26.5l-3.4 5.6h2.8l-.8 4.4 3.6-5.8h-2.8z" fill="#22c55e" />
    <rect x="198" y="26.5" width="21" height="10" rx="3" fill="none" stroke="#b7bccb" stroke-width="1.2" />
    <rect x="200" y="28.5" width="17" height="6" rx="1.5" fill="#22c55e" class="art-charge" />
    <rect x="220" y="29.5" width="2" height="4" rx="1" fill="#b7bccb" />

    <circle cx="70" cy="62" r="12" fill="url(#auth-art-brand)" />
    <path
      d="M65 57.5l4 4.5-4 4.5m5.5 0h5"
      fill="none"
      stroke="#fff"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <text x="89" y="56.5" dominant-baseline="central" font-size="12.5" font-weight="600" fill="#111827">Codex</text>
    <circle cx="91.5" cy="70.5" r="2.5" fill="#22c55e" />
    <text x="97" y="70.5" dominant-baseline="central" font-size="10" fill="#6b7280">在线</text>
    <path d="M48 84H236" stroke="#eceef3" />

    <g font-size="11.5" dominant-baseline="central">
      <rect x="110" y="94" width="116" height="28" rx="14" fill="url(#auth-art-brand)" />
      <text x="214" y="108" text-anchor="end" fill="#fff">帮我总结本周任务</text>

      <rect x="134" y="157" width="82" height="28" rx="14" fill="#fff" stroke="#e6e8f2" />
      <text x="146" y="171" fill="#6b7280">一切顺利。</text>

      <!-- on API credit the same request gets a real report -->
      <rect x="58" y="267" width="130" height="44" rx="14" fill="#fff" stroke="#e6e8f2" />
      <text x="70" y="281" fill="#374151">本周完成 3 项重点：</text>
      <text x="70" y="297" fill="#374151">1. 负载均衡已上线</text>
      <rect x="161" y="290" width="1.6" height="14" rx="0.8" fill="#4f5bd5" class="art-blink" />
    </g>

    <!-- Codex on a throttled subscription: dizzy, out of charge, and all it answers is a one-liner -->
    <g transform="translate(52 127) scale(1.15)">
      <g fill="#fbbf24">
        <path d="M9 9l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3-2.3-.9 2.3-.9z" class="art-twinkle" />
        <path d="M57 5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" class="art-twinkle" style="animation-delay: -0.8s" />
      </g>
      <text
        x="65"
        y="21"
        text-anchor="middle"
        dominant-baseline="central"
        font-size="11"
        font-weight="700"
        fill="#f59e0b"
      >
        ?
      </text>
      <g class="art-wobble">
        <rect x="23.5" y="0.5" width="17" height="9" rx="2.5" fill="#fff" stroke="#ef4444" stroke-width="1.2" />
        <rect x="25.5" y="2.5" width="4" height="5" rx="1" fill="#ef4444" class="art-pulse" />
        <rect x="41" y="3.5" width="2" height="3" rx="1" fill="#ef4444" />
        <g fill="#fff" stroke="#dfe3f2">
          <rect x="3" y="32" width="7" height="15" rx="3.5" transform="rotate(15 6.5 32)" />
          <rect x="56" y="32" width="7" height="15" rx="3.5" transform="rotate(-15 59.5 32)" />
        </g>
        <rect x="18" y="53" width="11" height="7" rx="3.5" fill="#dfe3f2" />
        <rect x="37" y="53" width="11" height="7" rx="3.5" fill="#dfe3f2" />
        <rect x="8" y="14" width="50" height="42" rx="12" fill="#fff" stroke="#dfe3f2" />
        <circle cx="16" cy="20.5" r="1.5" fill="#fca5a5" />
        <circle cx="21" cy="20.5" r="1.5" fill="#fcd34d" />
        <circle cx="26" cy="20.5" r="1.5" fill="#86efac" />
        <rect x="13" y="25" width="40" height="26" rx="7" fill="#1f2333" />
        <g fill="none" stroke="#6ee7b7" stroke-width="1.2" stroke-linecap="round">
          <path d="M24.8 36.6a1.2 1.2 0 0 1 2.4 0 2.4 2.4 0 0 1-4.8 0 3.6 3.6 0 0 1 7.2 0" class="art-dizzy" />
          <path d="M38.8 36.6a1.2 1.2 0 0 1 2.4 0 2.4 2.4 0 0 1-4.8 0 3.6 3.6 0 0 1 7.2 0" class="art-dizzy" />
          <path d="M28 45.5q1.25-2.4 2.5 0t2.5 0 2.5 0 2.5 0" />
        </g>
        <path d="M34.6 46.4v1.2a1.7 1.7 0 0 0 3.4 0v-1.6" fill="#f9a8d4" />
      </g>
    </g>

    <g font-size="11" font-weight="600" dominant-baseline="central">
      <rect x="73" y="204" width="138" height="24" rx="12" fill="#fdf3e3" />
      <circle cx="89" cy="216" r="5" fill="none" stroke="#b45f06" stroke-width="1.4" />
      <path d="M89 213.4V216l1.8 1.2" fill="none" stroke="#b45f06" stroke-width="1.4" stroke-linecap="round" />
      <text x="98" y="216" fill="#b45f06">已达 5 小时用量上限</text>

      <rect x="70" y="235" width="144" height="24" rx="12" fill="#eef0fd" />
      <path d="M86.7 241.5L82.1 248h3.4l-1 4.5 4.6-6.5h-3.4z" fill="#4f5bd5" />
      <text x="94" y="247" fill="#3e49b9">已接入 API，满血继续</text>
    </g>

    <rect x="133" y="329" width="18" height="17" rx="6" fill="#fff" stroke="#dfe2f2" />

    <!-- the power bank -->
    <rect
      x="316"
      y="140"
      width="212"
      height="104"
      rx="24"
      fill="url(#auth-art-brand)"
      filter="url(#auth-art-bank-shadow)"
    />
    <rect x="316" y="140" width="212" height="56" rx="24" fill="url(#auth-art-shine)" />
    <circle cx="356" cy="180" r="20" fill="#fff" fill-opacity="0.18" />
    <path d="M358 168l-10 14h7l-2 10 11-15h-7z" fill="#fff" />
    <text x="388" y="171" dominant-baseline="central" font-size="16" font-weight="700" fill="#fff">AI 充电宝</text>
    <rect x="463" y="162" width="34" height="18" rx="9" fill="#fff" fill-opacity="0.22" />
    <text
      x="480"
      y="171"
      text-anchor="middle"
      dominant-baseline="central"
      font-size="10.5"
      font-weight="600"
      fill="#fff"
    >
      满血
    </text>
    <text x="388" y="192" dominant-baseline="central" font-size="12.5" fill="#fff" fill-opacity="0.85">
      余额 {{ money(50) }}
    </text>
    <rect
      v-for="i in 4"
      :key="i"
      :x="388 + (i - 1) * 15"
      y="214"
      width="11"
      height="5"
      rx="2.5"
      fill="#fff"
      :class="{ 'art-pulse': i === 4 }"
    />
    <rect x="297" y="201" width="20" height="18" rx="6" fill="#fff" stroke="#dfe2f2" />
  </svg>
</template>

<script setup>
import { money } from '@/utils/format'

// Drawn from the power bank to the phone, so the flowing dashes run towards the phone. It dips below
// the phone's bottom edge before rising into the port.
const cable = 'M298 210C262 210 280 372 216 372H176C154 372 142 364 142 346'
</script>

<style scoped>
.art-flow {
  stroke-dasharray: 5 11;
  animation: art-flow 1.2s linear infinite;
}
.art-charge {
  transform-box: fill-box;
  transform-origin: left center;
  animation: art-charge 4s ease-out infinite;
}
.art-blink {
  animation: art-blink 1.1s steps(1) infinite;
}
.art-pulse {
  animation: art-pulse 1.8s ease-in-out infinite;
}
/* the throttled Codex: spinning spiral eyes, a sway from its feet and twinkling stars */
.art-dizzy {
  transform-box: fill-box;
  transform-origin: center;
  animation: art-spin 1.4s linear infinite;
}
.art-wobble {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  animation: art-wobble 2.6s ease-in-out infinite;
}
.art-twinkle {
  transform-box: fill-box;
  transform-origin: center;
  animation: art-twinkle 1.6s ease-in-out infinite;
}
@keyframes art-flow {
  to {
    stroke-dashoffset: -32;
  }
}
@keyframes art-charge {
  0% {
    transform: scaleX(0.15);
  }
  70%,
  100% {
    transform: scaleX(1);
  }
}
@keyframes art-blink {
  50% {
    opacity: 0;
  }
}
@keyframes art-pulse {
  50% {
    opacity: 0.35;
  }
}
@keyframes art-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes art-wobble {
  0%,
  100% {
    transform: rotate(-4deg);
  }
  50% {
    transform: rotate(4deg);
  }
}
@keyframes art-twinkle {
  50% {
    opacity: 0.25;
    transform: scale(0.6);
  }
}
@media (prefers-reduced-motion: reduce) {
  .art-flow,
  .art-charge,
  .art-blink,
  .art-pulse,
  .art-dizzy,
  .art-wobble,
  .art-twinkle {
    animation: none;
  }
}
</style>
