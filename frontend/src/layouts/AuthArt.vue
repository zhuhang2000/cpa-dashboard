<template>
  <svg
    viewBox="36 0 496 384"
    preserveAspectRatio="xMinYMid meet"
    role="img"
    aria-label="订阅额度触发 5 小时限制后，接上 AI 充电宝，对话马上接着进行"
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

    <!-- the phone: a chat that hits the subscription limit and carries on on API credit -->
    <rect x="40" y="10" width="204" height="320" rx="30" fill="#fff" stroke="#e6e8f2" filter="url(#auth-art-shadow)" />
    <rect x="48" y="18" width="188" height="304" rx="23" fill="#f7f8fc" />
    <rect x="120" y="25" width="44" height="13" rx="6.5" fill="#1f2333" />

    <text x="62" y="31.5" dominant-baseline="central" font-size="11" font-weight="600" fill="#111827">9:41</text>
    <path d="M192 26.5l-3.4 5.6h2.8l-.8 4.4 3.6-5.8h-2.8z" fill="#22c55e" />
    <rect x="198" y="26.5" width="21" height="10" rx="3" fill="none" stroke="#b7bccb" stroke-width="1.2" />
    <rect x="200" y="28.5" width="17" height="6" rx="1.5" fill="#22c55e" class="art-charge" />
    <rect x="220" y="29.5" width="2" height="4" rx="1" fill="#b7bccb" />

    <circle cx="70" cy="62" r="12" fill="url(#auth-art-brand)" />
    <path d="M70 55.5l1.7 4.8 4.8 1.7-4.8 1.7L70 68.5l-1.7-4.8-4.8-1.7 4.8-1.7z" fill="#fff" />
    <text x="89" y="56.5" dominant-baseline="central" font-size="12.5" font-weight="600" fill="#111827">AI 助手</text>
    <circle cx="91.5" cy="70.5" r="2.5" fill="#22c55e" />
    <text x="97" y="70.5" dominant-baseline="central" font-size="10" fill="#6b7280">在线</text>
    <path d="M48 84H236" stroke="#eceef3" />

    <g font-size="11.5" dominant-baseline="central">
      <rect x="110" y="96" width="116" height="28" rx="14" fill="url(#auth-art-brand)" />
      <text x="214" y="110" text-anchor="end" fill="#fff">帮我写完这份周报</text>

      <rect x="58" y="132" width="152" height="28" rx="14" fill="#fff" stroke="#e6e8f2" />
      <text x="70" y="146" fill="#374151">好的，先整理本周进展…</text>

      <rect x="58" y="240" width="140" height="28" rx="14" fill="#fff" stroke="#e6e8f2" />
      <text x="70" y="254" fill="#374151">接着写：下周计划是</text>
      <rect x="176" y="247" width="1.6" height="14" rx="0.8" fill="#4f5bd5" class="art-blink" />
    </g>

    <g font-size="11" font-weight="600" dominant-baseline="central">
      <rect x="73" y="172" width="138" height="24" rx="12" fill="#fdf3e3" />
      <circle cx="89" cy="184" r="5" fill="none" stroke="#b45f06" stroke-width="1.4" />
      <path d="M89 181.4V184l1.8 1.2" fill="none" stroke="#b45f06" stroke-width="1.4" stroke-linecap="round" />
      <text x="98" y="184" fill="#b45f06">已达 5 小时用量上限</text>

      <rect x="70" y="204" width="144" height="24" rx="12" fill="#eef0fd" />
      <path d="M86.7 210.5L82.1 217h3.4l-1 4.5 4.6-6.5h-3.4z" fill="#4f5bd5" />
      <text x="94" y="216" fill="#3e49b9">已接入 API，继续使用</text>
    </g>

    <rect x="58" y="282" width="168" height="28" rx="14" fill="#fff" stroke="#e6e8f2" />
    <text x="72" y="296" dominant-baseline="central" font-size="11" fill="#9ca3af">继续提问…</text>
    <circle cx="212" cy="296" r="10" fill="url(#auth-art-brand)" />
    <path
      d="M212 300.5v-9m-4 4 4-4 4 4"
      fill="none"
      stroke="#fff"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
    />

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
@media (prefers-reduced-motion: reduce) {
  .art-flow,
  .art-charge,
  .art-blink,
  .art-pulse {
    animation: none;
  }
}
</style>
