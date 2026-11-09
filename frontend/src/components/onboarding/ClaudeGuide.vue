<template>
  <svg class="claude-guide" viewBox="0 5 36 21" shape-rendering="crispEdges" aria-hidden="true" focusable="false">
    <!-- 充值页 ClaudeArt 的同一个人物：帽子、扫帚、身体、眼睛、短腿逐格照搬，整体左右镜像（x → 32 − x − 宽度）， -->
    <!-- 变成朝右飞向要引导的按钮，帽尖被风吹向身后。坐标单位为一个像素格，每格 3px，与充值页同尺寸 -->
    <!-- 新手引导姿势：后翼垂下扶着扫帚杆，前翼举着一把钥匙递向按钮，钥匙上方一颗闪光 -->
    <g class="rider">
      <!-- 钥匙上方的闪光 -->
      <g class="sparkle" fill="#efb154">
        <rect x="33" y="9" width="1" height="1" />
        <rect x="32" y="10" width="3" height="1" />
        <rect x="33" y="11" width="1" height="1" />
      </g>
      <rect class="sparkle-dot" x="35" y="11" width="1" height="1" fill="#efb154" />
      <!-- 帽尖两帧：翘起 / 被风吹垂 -->
      <g class="tip-a">
        <g class="hat" fill="#2f2f2d">
          <rect x="14" y="5" width="2" height="1" />
          <rect x="15" y="6" width="4" height="1" />
        </g>
      </g>
      <g class="tip-b">
        <g class="hat" fill="#2f2f2d">
          <rect x="14" y="6" width="5" height="1" />
          <rect x="13" y="7" width="2" height="1" />
        </g>
      </g>
      <!-- 扫帚穗两帧 -->
      <g class="straw-a">
        <g fill="#603813">
          <rect x="1" y="18" width="1" height="1" />
          <rect x="3" y="19" width="1" height="1" />
          <rect x="1" y="21" width="3" height="1" />
          <rect x="0" y="22" width="1" height="1" />
          <rect x="1" y="23" width="1" height="2" />
          <rect x="11" y="24" width="2" height="1" />
        </g>
        <g fill="#bd8333">
          <rect x="4" y="18" width="1" height="2" />
          <rect x="8" y="19" width="1" height="1" />
          <rect x="6" y="20" width="1" height="1" />
          <rect x="2" y="20" width="1" height="1" />
          <rect x="10" y="21" width="1" height="4" />
          <rect x="4" y="21" width="4" height="1" />
          <rect x="12" y="22" width="1" height="2" />
          <rect x="5" y="23" width="1" height="1" />
          <rect x="2" y="23" width="1" height="1" />
          <rect x="8" y="24" width="1" height="1" />
          <rect x="9" y="25" width="1" height="1" />
          <rect x="6" y="25" width="1" height="1" />
          <rect x="4" y="25" width="1" height="1" />
        </g>
        <g fill="#efb154">
          <rect x="3" y="18" width="1" height="1" />
          <rect x="7" y="19" width="1" height="1" />
          <rect x="5" y="19" width="1" height="1" />
          <rect x="9" y="20" width="1" height="1" />
          <rect x="3" y="20" width="2" height="1" />
          <rect x="8" y="21" width="1" height="1" />
          <rect x="11" y="22" width="1" height="2" />
          <rect x="6" y="22" width="1" height="1" />
          <rect x="1" y="22" width="3" height="1" />
          <rect x="9" y="23" width="1" height="2" />
          <rect x="6" y="23" width="2" height="1" />
          <rect x="3" y="23" width="2" height="1" />
          <rect x="2" y="24" width="1" height="1" />
          <rect x="7" y="25" width="1" height="1" />
          <rect x="5" y="25" width="1" height="1" />
        </g>
        <g fill="#f4db9a">
          <rect x="6" y="19" width="1" height="1" />
          <rect x="7" y="20" width="2" height="1" />
          <rect x="5" y="20" width="1" height="1" />
          <rect x="9" y="21" width="1" height="1" />
          <rect x="7" y="22" width="3" height="1" />
          <rect x="4" y="22" width="2" height="1" />
          <rect x="8" y="23" width="1" height="1" />
          <rect x="3" y="24" width="5" height="1" />
          <rect x="8" y="25" width="1" height="1" />
        </g>
      </g>
      <g class="straw-b">
        <g fill="#603813">
          <rect x="3" y="18" width="1" height="1" />
          <rect x="2" y="20" width="1" height="2" />
          <rect x="0" y="23" width="1" height="1" />
          <rect x="11" y="24" width="2" height="1" />
        </g>
        <g fill="#bd8333">
          <rect x="5" y="18" width="1" height="1" />
          <rect x="0" y="18" width="1" height="1" />
          <rect x="8" y="19" width="1" height="1" />
          <rect x="3" y="19" width="1" height="1" />
          <rect x="6" y="20" width="1" height="1" />
          <rect x="10" y="21" width="1" height="4" />
          <rect x="6" y="21" width="2" height="1" />
          <rect x="3" y="21" width="1" height="1" />
          <rect x="12" y="22" width="1" height="2" />
          <rect x="0" y="22" width="1" height="1" />
          <rect x="5" y="23" width="1" height="1" />
          <rect x="8" y="24" width="1" height="1" />
          <rect x="2" y="24" width="1" height="1" />
          <rect x="9" y="25" width="1" height="1" />
          <rect x="5" y="25" width="1" height="1" />
        </g>
        <g fill="#efb154">
          <rect x="4" y="18" width="1" height="1" />
          <rect x="7" y="19" width="1" height="1" />
          <rect x="4" y="19" width="2" height="1" />
          <rect x="9" y="20" width="1" height="1" />
          <rect x="3" y="20" width="1" height="1" />
          <rect x="8" y="21" width="1" height="1" />
          <rect x="4" y="21" width="2" height="1" />
          <rect x="11" y="22" width="1" height="2" />
          <rect x="6" y="22" width="1" height="1" />
          <rect x="3" y="22" width="1" height="1" />
          <rect x="1" y="22" width="1" height="1" />
          <rect x="9" y="23" width="1" height="2" />
          <rect x="6" y="23" width="2" height="1" />
          <rect x="4" y="23" width="1" height="1" />
          <rect x="1" y="23" width="2" height="1" />
          <rect x="3" y="24" width="2" height="1" />
          <rect x="6" y="25" width="2" height="1" />
        </g>
        <g fill="#f4db9a">
          <rect x="6" y="19" width="1" height="1" />
          <rect x="7" y="20" width="2" height="1" />
          <rect x="4" y="20" width="2" height="1" />
          <rect x="9" y="21" width="1" height="1" />
          <rect x="7" y="22" width="3" height="1" />
          <rect x="4" y="22" width="2" height="1" />
          <rect x="2" y="22" width="1" height="1" />
          <rect x="8" y="23" width="1" height="1" />
          <rect x="3" y="23" width="1" height="1" />
          <rect x="5" y="24" width="3" height="1" />
          <rect x="8" y="25" width="1" height="1" />
        </g>
      </g>
      <!-- 后翼垂下扶着扫帚杆 -->
      <g fill="#d97757">
        <rect x="14" y="18" width="1" height="1" />
        <rect x="13" y="19" width="1" height="1" />
      </g>
      <g fill="#bd674d">
        <rect x="14" y="19" width="1" height="3" />
      </g>
      <!-- 前翼举着钥匙（钥匙环、钥匙杆、齿），手和钥匙一起上下 -->
      <g class="arm">
        <g fill="#f4db9a">
          <rect x="29" y="13" width="1" height="1" />
        </g>
        <g fill="#efb154">
          <rect x="30" y="13" width="2" height="1" />
          <rect x="29" y="14" width="1" height="1" />
          <rect x="31" y="14" width="5" height="1" />
        </g>
        <g fill="#bd8333">
          <rect x="29" y="15" width="3" height="1" />
          <rect x="34" y="15" width="2" height="1" />
          <rect x="35" y="16" width="1" height="1" />
        </g>
        <g fill="#d97757">
          <rect x="28" y="14" width="1" height="1" />
          <rect x="27" y="15" width="2" height="1" />
          <rect x="26" y="16" width="2" height="1" />
        </g>
        <g fill="#bd674d">
          <rect x="28" y="16" width="1" height="1" />
          <rect x="26" y="17" width="2" height="1" />
        </g>
      </g>
      <!-- 短腿两帧 -->
      <g class="leg-a">
        <g fill="#d97757">
          <rect x="24" y="21" width="2" height="1" />
          <rect x="16" y="21" width="2" height="1" />
        </g>
      </g>
      <g class="leg-b">
        <g fill="#d97757">
          <rect x="20" y="21" width="2" height="1" />
        </g>
        <g fill="#bd674d">
          <rect x="14" y="21" width="1" height="1" />
        </g>
      </g>
      <!-- 帽身、身体、扫帚杆 -->
      <g class="hat" fill="#2f2f2d">
        <rect x="17" y="7" width="5" height="1" />
        <rect x="17" y="8" width="6" height="2" />
        <rect x="17" y="10" width="7" height="1" />
        <rect x="15" y="11" width="10" height="1" />
        <rect x="12" y="12" width="17" height="1" />
        <rect x="26" y="13" width="2" height="1" />
        <rect x="13" y="13" width="2" height="1" />
      </g>
      <g fill="#d97757">
        <rect x="24" y="14" width="2" height="2" />
        <rect x="18" y="14" width="5" height="2" />
        <rect x="15" y="14" width="2" height="2" />
        <rect x="15" y="16" width="10" height="1" />
        <rect x="16" y="17" width="9" height="1" />
        <rect x="16" y="18" width="10" height="2" />
        <rect x="24" y="20" width="2" height="1" />
        <rect x="20" y="20" width="2" height="1" />
        <rect x="17" y="20" width="1" height="1" />
      </g>
      <g fill="#bd674d">
        <rect x="15" y="13" width="11" height="1" />
        <rect x="23" y="14" width="1" height="2" />
        <rect x="17" y="14" width="1" height="2" />
        <rect x="25" y="16" width="1" height="2" />
        <rect x="15" y="17" width="1" height="3" />
        <rect x="22" y="20" width="2" height="1" />
        <rect x="18" y="20" width="2" height="1" />
        <rect x="14" y="20" width="3" height="1" />
      </g>
      <g fill="#603813">
        <rect x="29" y="20" width="2" height="1" />
        <rect x="26" y="21" width="3" height="1" />
        <rect x="13" y="22" width="14" height="1" />
      </g>
      <g fill="#2f1800">
        <rect x="31" y="20" width="1" height="1" />
        <rect x="29" y="21" width="2" height="1" />
        <rect x="27" y="22" width="2" height="1" />
        <rect x="13" y="23" width="12" height="1" />
      </g>
      <!-- 眼睛 -->
      <g class="eyes">
        <g fill="#000000">
          <rect x="24" y="14" width="1" height="2" />
          <rect x="18" y="14" width="1" height="2" />
        </g>
      </g>
    </g>
  </svg>
</template>

<style scoped>
/* ClaudeArt's broom rider as the onboarding guide, flying at the button it hands a key to. Three screen pixels
   per cell, the size ClaudeArt is drawn at on the redeem card. Not clipped, so the hover can carry the hat
   above the box. */
.claude-guide {
  display: block;
  width: 108px;
  height: 63px;
  overflow: visible;
}
/* The near-black hat would sink into a dark card; a slate grey still reads as a black hat (as in ClaudeArt). */
:root[data-theme='dark'] .hat {
  fill: #4a4d57;
}

/* The rider hovers and tilts nose-up as in ClaudeArt, mirrored since it flies right; hat tip, straw and legs
   swap between two pixel frames. The hand lifts the key now and then, and the sparkle above it twinkles. */
.rider {
  animation: fly-ride 2.6s ease-in-out infinite;
  transform-origin: 13px 16px;
}
.tip-a {
  animation: frame-a 0.8s step-end infinite;
}
.tip-b {
  animation: frame-b 0.8s step-end infinite;
}
.straw-a {
  animation: frame-a 0.36s step-end infinite;
}
.straw-b {
  animation: frame-b 0.36s step-end infinite;
}
.leg-a {
  animation: frame-a 0.56s step-end infinite;
}
.leg-b {
  animation: frame-b 0.56s step-end infinite;
}
.arm {
  animation: lift 1.12s step-end infinite;
}
.sparkle {
  animation: twinkle 1.2s step-end infinite;
}
.sparkle-dot {
  animation: twinkle 1.2s step-end 0.6s infinite;
}
/* Blink: the two-cell-tall eyes squash to one cell. */
.eyes {
  animation: blink 4s step-end infinite;
  transform-origin: 0 16px;
}

@keyframes fly-ride {
  0%,
  100% {
    transform: translate(0, 0) rotate(-1deg);
  }
  50% {
    transform: translate(0.7px, -1.5px) rotate(-4deg);
  }
}
@keyframes frame-a {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
@keyframes frame-b {
  0% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}
@keyframes lift {
  0% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-1px);
  }
}
@keyframes twinkle {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
@keyframes blink {
  0% {
    transform: scaleY(1);
  }
  93% {
    transform: scaleY(0.5);
  }
  97% {
    transform: scaleY(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .rider,
  .tip-a,
  .straw-a,
  .leg-a,
  .arm,
  .sparkle,
  .sparkle-dot,
  .eyes {
    animation: none;
  }
  .tip-b,
  .straw-b,
  .leg-b {
    display: none;
  }
}
</style>
