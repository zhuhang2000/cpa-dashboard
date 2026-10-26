<template>
  <svg
    viewBox="36 0 456 516"
    preserveAspectRatio="xMinYMid meet"
    role="img"
    aria-label="实验两周没有效果，向 Codex 寻求论文建议。低电量时只给出笼统建议；接上 AI 充电宝后，继续分析对照组设计与评价指标。"
  >
    <defs>
      <linearGradient id="auth-art-brand" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#4f5bd5" />
        <stop offset="1" stop-color="#8b5cf6" />
      </linearGradient>
      <linearGradient id="auth-art-shell" x1="0" y1="0" x2="0.6" y2="1">
        <stop offset="0" stop-color="#fff" />
        <stop offset="0.55" stop-color="#f9f8ff" />
        <stop offset="1" stop-color="#dddaf5" />
      </linearGradient>
      <linearGradient id="auth-art-face" x1="0" y1="0" x2="0.8" y2="1">
        <stop offset="0" stop-color="#343450" />
        <stop offset="1" stop-color="#191a30" />
      </linearGradient>
      <linearGradient id="auth-art-visor-shine" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#c4b5fd" stop-opacity="0.2" />
        <stop offset="1" stop-color="#c4b5fd" stop-opacity="0" />
      </linearGradient>
      <linearGradient id="auth-art-bank-body" x1="0" y1="0" x2="0.6" y2="1">
        <stop offset="0" stop-color="#faf8ff" />
        <stop offset="0.55" stop-color="#f0ecff" />
        <stop offset="1" stop-color="#e2dafc" />
      </linearGradient>
      <linearGradient id="auth-art-screen" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#fff" />
        <stop offset="1" stop-color="#f5f3ff" />
      </linearGradient>
      <linearGradient id="auth-art-gauge" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#6ee7b7" />
        <stop offset="1" stop-color="#10b981" />
      </linearGradient>
      <!-- userSpaceOnUse so the colour runs along the cable, from the power bank to the phone -->
      <linearGradient id="auth-art-cable" gradientUnits="userSpaceOnUse" x1="404" y1="0" x2="156" y2="0">
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
      <filter id="auth-art-bank-shadow" x="-40%" y="-30%" width="180%" height="160%">
        <feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#6d5ce8" flood-opacity="0.2" />
      </filter>
      <filter id="auth-art-bot-shadow" x="-30%" y="-30%" width="160%" height="170%">
        <feDropShadow dx="0" dy="2" stdDeviation="1.5" flood-color="#6556a8" flood-opacity="0.14" />
      </filter>
    </defs>

    <circle cx="156" cy="246" r="210" fill="url(#auth-art-glow)" />
    <circle cx="404" cy="302" r="120" fill="url(#auth-art-glow)" />

    <!-- the charging cable runs from the power bank's bottom port to the phone's -->
    <g fill="none" stroke-linecap="round">
      <path :d="cable" stroke="#dfe3fb" stroke-width="5" />
      <path :d="cable" stroke="url(#auth-art-cable)" stroke-width="2.2" class="art-flow" />
    </g>

    <!-- the phone, at a modern ~1:2 aspect so the chat reads like a real AI app -->
    <rect x="40" y="10" width="232" height="472" rx="36" fill="#fff" stroke="#e6e8f2" filter="url(#auth-art-shadow)" />
    <rect x="48" y="18" width="216" height="456" rx="28" fill="#f7f8fc" />
    <rect x="134" y="25" width="44" height="13" rx="6.5" fill="#1f2333" />

    <text x="65" y="32" dominant-baseline="central" font-size="11" font-weight="600" fill="#111827">9:41</text>
    <path d="M220 26.5l-3.4 5.6h2.8l-.8 4.4 3.6-5.8h-2.8z" fill="#22c55e" />
    <rect x="226" y="26.5" width="21" height="10" rx="3" fill="none" stroke="#b7bccb" stroke-width="1.2" />
    <rect x="228" y="28.5" width="17" height="6" rx="1.5" fill="#22c55e" class="art-charge" />
    <rect x="248" y="29.5" width="2" height="4" rx="1" fill="#b7bccb" />

    <circle cx="70" cy="64" r="12" fill="url(#auth-art-brand)" />
    <path
      d="M65 59.5l4 4.5-4 4.5m5.5 0h5"
      fill="none"
      stroke="#fff"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <text x="89" y="58" dominant-baseline="central" font-size="12.5" font-weight="600" fill="#111827">Codex</text>
    <circle cx="91.5" cy="73" r="2.5" fill="#22c55e" />
    <text x="97" y="73" dominant-baseline="central" font-size="10" fill="#6b7280">在线</text>
    <path d="M48 94H264" stroke="#eceef3" />

    <g font-size="11.5" dominant-baseline="central">
      <rect x="96" y="106" width="154" height="46" rx="15" fill="url(#auth-art-brand)" />
      <text fill="#fff">
        <tspan x="110" y="120">实验跑了两周都没效果，</tspan>
        <tspan x="110" y="139">论文还有救吗？</tspan>
      </text>

      <!-- On low charge it barely thinks and lists the usual platitudes. -->
      <path
        d="M152 164h84a14 14 0 0 1 14 14v54a14 14 0 0 1-14 14h-84a14 14 0 0 1-14-14v-22l-6-5 6-5v-22a14 14 0 0 1 14-14Z"
        fill="#fff"
        stroke="#e4e2f1"
      />
      <path d="M154 175.5l1 2.6 2.6 1-2.6 1-1 2.6-1-2.6-2.6-1 2.6-1Z" fill="#c3c0d4" />
      <text x="161" y="180" font-size="9.5" fill="#a8a5bd">已思考 1 秒</text>
      <g fill="#858298">
        <text x="150" y="198">
          <tspan fill="#aeabc2">1.</tspan>
          <tspan x="163" font-weight="600">扩大数据量</tspan>
        </text>
        <text x="150" y="215">
          <tspan fill="#aeabc2">2.</tspan>
          <tspan x="163" font-weight="600">优化实验方法</tspan>
        </text>
        <text x="150" y="232">
          <tspan fill="#aeabc2">3.</tspan>
          <tspan x="163" font-weight="600">多看相关论文</tspan>
        </text>
      </g>

      <!-- After charging it thinks the problem through and answers with concrete checks. -->
      <path d="M67 325.5l1.2 3.3 3.3 1.2-3.3 1.2-1.2 3.3-1.2-3.3-3.3-1.2 3.3-1.2Z" fill="#7c6cf0" />
      <text x="76" y="330" font-size="10" fill="#8a87a6">已深度思考 48 秒</text>
      <path d="M157 327.5l2.5 2.5-2.5 2.5" fill="none" stroke="#b3b0c8" stroke-width="1.2" stroke-linecap="round" />
      <text x="62" y="350" font-size="12.5" font-weight="650" fill="#1f2333">先别急着换题。</text>
      <text x="62" y="369" fill="#4b5063">我们排查几个关键问题：</text>
      <circle cx="67" cy="389" r="1.8" fill="#8b85c3" />
      <circle cx="67" cy="409" r="1.8" fill="#8b85c3" />
      <!-- Each run sits in its own tspan: loose text after a tspan would pick up a space from the line break. -->
      <text x="74" y="389" fill="#4b5063">
        <tspan font-weight="600" fill="#1f2333">对照组</tspan>
        <tspan>：</tspan>
      </text>
      <text x="74" y="409" fill="#4b5063">
        <tspan font-weight="600" fill="#1f2333">评价指标</tspan>
        <tspan>：</tspan>
      </text>
      <rect x="118" y="381" width="56" height="16" rx="4" fill="#eef0fd" />
      <rect x="130" y="401" width="26" height="16" rx="4" fill="#eef0fd" />
      <g font-family="'SF Mono', Menlo, Consolas, monospace" font-size="10" text-anchor="middle" fill="#4f46e5">
        <text x="146" y="389">baseline</text>
        <text x="143" y="409">AUC</text>
      </g>
      <text x="178" y="389" fill="#4b5063">是否复现</text>
      <text x="160" y="409" fill="#4b5063">够不够敏感</text>
      <rect x="220" y="402" width="1.6" height="14" rx="0.8" fill="#4f5bd5" class="art-blink" />
    </g>

    <!-- A little terminal robot: a low-battery antenna, spiral eyes and a dazed expression. -->
    <g transform="translate(54 165)">
      <ellipse cx="38" cy="68" rx="23" ry="3" fill="#d9d5ee" opacity="0.55" />
      <path d="M6 20C7 8 59 4 69 19" fill="none" stroke="#e6def9" stroke-width="1.2" stroke-dasharray="2 4" />
      <path d="m7 11 1.3 3.3 3.3 1.3-3.3 1.3L7 20.2l-1.3-3.3-3.3-1.3 3.3-1.3Z" fill="#f6c66c" class="art-twinkle" />
      <path
        d="m64 7 .9 2.4 2.4.9-2.4.9L64 13.6l-.9-2.4-2.4-.9 2.4-.9Z"
        fill="#b7a4ee"
        class="art-twinkle"
        style="animation-delay: -1.2s"
      />
      <text
        x="71"
        y="27"
        text-anchor="middle"
        dominant-baseline="central"
        font-size="12"
        font-weight="700"
        fill="#c9a369"
        transform="rotate(12 71 27)"
      >
        ?
      </text>
      <g class="art-wobble">
        <path d="M37 21v-4q0-4-4-4" fill="none" stroke="#b3aacd" stroke-width="2" stroke-linecap="round" />
        <g transform="rotate(-9 32 8)">
          <rect x="22" y="3" width="21" height="11" rx="3.5" fill="#fff5f3" stroke="#ed8c8c" stroke-width="1.3" />
          <rect x="24.5" y="5.5" width="4.5" height="6" rx="1.5" fill="#f08080" class="art-low-battery" />
          <path d="M31.5 6.5v3m0 1.1v.1" stroke="#e6a09a" stroke-width="1.3" stroke-linecap="round" />
          <rect x="43" y="6.5" width="2.5" height="4" rx="1.2" fill="#ed8c8c" />
        </g>
        <g fill="url(#auth-art-shell)" stroke="#cfc9e6" stroke-width="1.1">
          <rect x="3.5" y="39" width="8" height="17" rx="4" transform="rotate(13 7.5 39)" />
          <rect x="65" y="37" width="8" height="17" rx="4" transform="rotate(-17 69 37)" />
          <rect x="21" y="59" width="13" height="8" rx="4" />
          <rect x="44" y="59" width="13" height="8" rx="4" />
        </g>
        <g filter="url(#auth-art-bot-shadow)">
          <rect
            x="9"
            y="18"
            width="59"
            height="45"
            rx="15"
            fill="url(#auth-art-shell)"
            stroke="#ccc5e4"
            stroke-width="1.2"
          />
          <path d="M15 30q0-7 8-7h29" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" />
          <circle cx="21" cy="25" r="1.5" fill="#eea5ad" />
          <circle cx="26" cy="25" r="1.5" fill="#eac780" />
          <circle cx="31" cy="25" r="1.5" fill="#93cdbf" />
          <path d="m53 23 2 2-2 2m5 0h3" fill="none" stroke="#b6a9d2" stroke-width="1.1" stroke-linecap="round" />
          <rect
            x="14"
            y="30"
            width="49"
            height="28"
            rx="10"
            fill="url(#auth-art-face)"
            stroke="#bfb6d9"
            stroke-width="0.8"
          />
          <path d="M24 31h29q9 0 9 9H15q0-9 9-9Z" fill="url(#auth-art-visor-shine)" />
          <g fill="none" stroke="#a5f0db" stroke-width="1.5" stroke-linecap="round">
            <path
              d="M28 41a1.2 1.2 0 1 1 2.4 0 2.4 2.4 0 1 1-4.8 0 3.6 3.6 0 1 1 7.2 0 4.8 4.8 0 0 1-4.8 4.8"
              class="art-dizzy"
            />
            <path
              d="M47 41a1.2 1.2 0 1 1 2.4 0 2.4 2.4 0 1 1-4.8 0 3.6 3.6 0 1 1 7.2 0 4.8 4.8 0 0 1-4.8 4.8"
              class="art-dizzy art-dizzy-right"
            />
          </g>
          <ellipse cx="22" cy="49" rx="3" ry="1.5" fill="#e8a6c4" opacity="0.5" />
          <ellipse cx="55" cy="49" rx="3" ry="1.5" fill="#e8a6c4" opacity="0.5" />
          <path d="M33 50q2.5-2.5 5 0t5 0" fill="none" stroke="#c2e3e0" stroke-width="1.5" stroke-linecap="round" />
          <path d="M38.5 50.8v1.5a2 2 0 0 0 4 0v-1.9" fill="#f2adc6" />
          <path d="M32 60.5h13" stroke="#c4bcdf" stroke-width="1.2" stroke-linecap="round" />
        </g>
      </g>
    </g>

    <g font-size="11" font-weight="600" dominant-baseline="central">
      <!-- Both notices share one width, each icon-and-text run centred on the screen. -->
      <rect x="75" y="258" width="162" height="24" rx="12" fill="#fdf3e3" />
      <circle cx="103.4" cy="270" r="5" fill="none" stroke="#b45f06" stroke-width="1.4" />
      <path d="M103.4 267.4V270l1.8 1.2" fill="none" stroke="#b45f06" stroke-width="1.4" stroke-linecap="round" />
      <text x="113.4" y="270" fill="#b45f06">已达 5 小时用量上限</text>

      <rect x="75" y="290" width="162" height="24" rx="12" fill="#eef0fd" />
      <path d="M94.1 296.5L89.5 303h3.4l-1 4.5 4.6-6.5h-3.4z" fill="#4f5bd5" />
      <text x="101.5" y="302" fill="#3e49b9">已接上充电宝，继续分析</text>
    </g>

    <rect x="60" y="428" width="192" height="28" rx="14" fill="#fff" stroke="#e6e8f2" />
    <text x="74" y="442" dominant-baseline="central" font-size="11" fill="#9ca3af">给 Codex 发消息</text>
    <circle cx="238" cy="442" r="10" fill="url(#auth-art-brand)" />
    <path
      d="M238 446.5v-9m-4 4 4-4 4 4"
      fill="none"
      stroke="#fff"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <rect x="124" y="464" width="64" height="4" rx="2" fill="#1f2333" fill-opacity="0.8" />

    <rect x="146" y="481" width="20" height="18" rx="6" fill="#fff" stroke="#dfe2f2" />

    <!-- the power bank: a pocket brick level with the charging status in the chat, with a side button, a darker
         band for its thickness and the cable in its bottom port -->
    <rect x="472" y="232" width="5" height="22" rx="2.5" fill="#c9bdf2" />
    <rect x="334" y="209" width="140" height="196" rx="28" fill="#d3c8f6" filter="url(#auth-art-bank-shadow)" />
    <rect x="334" y="202" width="140" height="196" rx="28" fill="url(#auth-art-bank-body)" stroke="#d9d0f7" />
    <rect x="335.5" y="203.5" width="137" height="193" rx="26.5" fill="none" stroke="#fff" stroke-opacity="0.85" />

    <!-- its display reads the API balance as the charge left -->
    <rect x="348" y="216" width="112" height="76" rx="15" fill="url(#auth-art-screen)" stroke="#e3ddf9" />
    <text x="360" y="231" dominant-baseline="central" font-size="9" fill="#8a84b8">API 余额</text>
    <path d="M447.6 226l-3.8 5.4h2.8l-.8 4.2 3.8-5.4h-2.8z" fill="#10b981" class="art-pulse" />
    <text x="359" y="253" dominant-baseline="central" font-size="20" font-weight="700" fill="#3e49b9">
      {{ money(50) }}
    </text>
    <rect
      v-for="i in 5"
      :key="i"
      :x="360 + (i - 1) * 13"
      y="272"
      width="11"
      height="7"
      rx="2"
      fill="url(#auth-art-gauge)"
      :class="{ 'art-pulse': i === 5 }"
    />
    <text x="429" y="275.5" dominant-baseline="central" font-size="9.5" font-weight="600" fill="#059669">满血</text>

    <rect x="357" y="336" width="20" height="20" rx="6" fill="url(#auth-art-brand)" />
    <path d="M368 340l-5 7h3.5l-1 5 5.5-7.5h-3.5z" fill="#fff" />
    <text x="383" y="346" dominant-baseline="central" font-size="16" font-weight="700" fill="url(#auth-art-brand)">
      AI 充电宝
    </text>
    <rect x="394" y="403" width="20" height="18" rx="6" fill="#fff" stroke="#dfe2f2" />
  </svg>
</template>

<script setup>
import { money } from '@/utils/format'

// Drawn from the power bank to the phone, so the flowing dashes run towards the phone. It drops from the
// bank's bottom port and runs under the phone before rising into its port at (156, 499).
const cable = 'M404 421C404 466 394 506 352 506H194C170 506 156 504 156 499'
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
/* Slow, slightly mismatched movements keep the little robot dazed without flickering. */
.art-dizzy {
  transform-box: fill-box;
  transform-origin: center;
  animation: art-spin 3.2s linear infinite;
}
.art-dizzy-right {
  animation-duration: 3.8s;
  animation-direction: reverse;
}
.art-wobble {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  animation: art-wobble 4s ease-in-out infinite;
}
.art-twinkle {
  transform-box: fill-box;
  transform-origin: center;
  animation: art-twinkle 2.8s ease-in-out infinite;
}
.art-low-battery {
  animation: art-low-battery 2.4s ease-in-out infinite;
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
    transform: rotate(-5deg);
  }
  50% {
    transform: rotate(3deg) translateY(0.5px);
  }
}
@keyframes art-twinkle {
  50% {
    opacity: 0.45;
    transform: scale(0.8);
  }
}
@keyframes art-low-battery {
  50% {
    opacity: 0.4;
  }
}
@media (prefers-reduced-motion: reduce) {
  .art-flow,
  .art-charge,
  .art-blink,
  .art-pulse,
  .art-dizzy,
  .art-wobble,
  .art-twinkle,
  .art-low-battery {
    animation: none;
  }
}
</style>
