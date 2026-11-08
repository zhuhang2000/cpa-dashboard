<template>
  <svg viewBox="0 12 240 192" shape-rendering="crispEdges" aria-hidden="true" focusable="false">
    <!-- 画在 240×240 网格上；viewBox 裁掉上下空白（太阳顶 18，最低火星约 200），画面 5:4 撑满容器 -->
    <!-- 像素格放大 6 倍入画；人物朝左飞，扫帚穗在身后，风景向右掠过 -->
    <!-- 白天：像素太阳（9×9 格，与月亮同位）；斜向光芒闪烁 -->
    <g class="sun" fill="#eaa53c">
      <rect x="174" y="30" width="18" height="6" />
      <rect x="168" y="36" width="30" height="18" />
      <rect x="174" y="54" width="18" height="6" />
      <rect x="180" y="18" width="6" height="6" />
      <rect x="180" y="66" width="6" height="6" />
      <rect x="156" y="42" width="6" height="6" />
      <rect x="204" y="42" width="6" height="6" />
      <g class="sun-glint">
        <rect x="162" y="24" width="6" height="6" />
        <rect x="198" y="24" width="6" height="6" />
        <rect x="162" y="60" width="6" height="6" />
        <rect x="198" y="60" width="6" height="6" />
      </g>
      <rect x="174" y="36" width="6" height="6" fill="#f4db9a" />
    </g>
    <!-- 夜晚：像素弯月 -->
    <g class="moon" fill="#eaa53c">
      <rect x="180" y="30" width="18" height="6" />
      <rect x="174" y="36" width="18" height="6" />
      <rect x="168" y="42" width="18" height="6" />
      <rect x="168" y="48" width="18" height="6" />
      <rect x="174" y="54" width="18" height="6" />
      <rect x="180" y="60" width="18" height="6" />
    </g>
    <rect class="star-1" x="42" y="42" width="6" height="6" fill="#efb154" />
    <rect class="star-2" x="132" y="24" width="6" height="6" fill="#7f8cf2" />
    <rect class="star-2" x="24" y="186" width="6" height="6" fill="#7f8cf2" />
    <g class="speed-line">
      <rect x="30" y="84" width="36" height="3" fill="#d97757" />
      <rect x="96" y="198" width="48" height="3" fill="#efb154" />
    </g>
    <g class="speed-line-late">
      <rect x="12" y="132" width="30" height="3" fill="#7f8cf2" />
      <rect x="150" y="186" width="30" height="3" fill="#d97757" />
    </g>
    <!-- 3. 核心：Claude 骑扫帚组合 -->
    <g class="rider">
      <!-- 3.1 扫帚穗喷出的火星 -->
      <rect class="spark-1" x="198" y="150" width="6" height="6" fill="#efb154" />
      <rect class="spark-2" x="192" y="168" width="6" height="6" fill="#f4db9a" />
      <rect class="spark-3" x="186" y="180" width="6" height="6" fill="#d97757" />
      <!-- 3.2 人物与扫帚（下列坐标单位为一个像素格） -->
      <g transform="translate(12 30) scale(6)">
        <!-- 帽尖两帧：翘起 / 被风吹垂 -->
        <g class="tip-a">
          <g class="hat" fill="#2f2f2d">
            <rect x="16" y="5" width="2" height="1" />
            <rect x="13" y="6" width="4" height="1" />
          </g>
        </g>
        <g class="tip-b">
          <g class="hat" fill="#2f2f2d">
            <rect x="13" y="6" width="5" height="1" />
            <rect x="17" y="7" width="2" height="1" />
          </g>
        </g>
        <!-- 扫帚穗两帧 -->
        <g class="straw-a">
          <g fill="#603813">
            <rect x="30" y="18" width="1" height="1" />
            <rect x="28" y="19" width="1" height="1" />
            <rect x="28" y="21" width="3" height="1" />
            <rect x="31" y="22" width="1" height="1" />
            <rect x="30" y="23" width="1" height="2" />
            <rect x="19" y="24" width="2" height="1" />
          </g>
          <g fill="#bd8333">
            <rect x="27" y="18" width="1" height="2" />
            <rect x="23" y="19" width="1" height="1" />
            <rect x="25" y="20" width="1" height="1" />
            <rect x="29" y="20" width="1" height="1" />
            <rect x="21" y="21" width="1" height="4" />
            <rect x="24" y="21" width="4" height="1" />
            <rect x="19" y="22" width="1" height="2" />
            <rect x="26" y="23" width="1" height="1" />
            <rect x="29" y="23" width="1" height="1" />
            <rect x="23" y="24" width="1" height="1" />
            <rect x="22" y="25" width="1" height="1" />
            <rect x="25" y="25" width="1" height="1" />
            <rect x="27" y="25" width="1" height="1" />
          </g>
          <g fill="#efb154">
            <rect x="28" y="18" width="1" height="1" />
            <rect x="24" y="19" width="1" height="1" />
            <rect x="26" y="19" width="1" height="1" />
            <rect x="22" y="20" width="1" height="1" />
            <rect x="27" y="20" width="2" height="1" />
            <rect x="23" y="21" width="1" height="1" />
            <rect x="20" y="22" width="1" height="2" />
            <rect x="25" y="22" width="1" height="1" />
            <rect x="28" y="22" width="3" height="1" />
            <rect x="22" y="23" width="1" height="2" />
            <rect x="24" y="23" width="2" height="1" />
            <rect x="27" y="23" width="2" height="1" />
            <rect x="29" y="24" width="1" height="1" />
            <rect x="24" y="25" width="1" height="1" />
            <rect x="26" y="25" width="1" height="1" />
          </g>
          <g fill="#f4db9a">
            <rect x="25" y="19" width="1" height="1" />
            <rect x="23" y="20" width="2" height="1" />
            <rect x="26" y="20" width="1" height="1" />
            <rect x="22" y="21" width="1" height="1" />
            <rect x="22" y="22" width="3" height="1" />
            <rect x="26" y="22" width="2" height="1" />
            <rect x="23" y="23" width="1" height="1" />
            <rect x="24" y="24" width="5" height="1" />
            <rect x="23" y="25" width="1" height="1" />
          </g>
        </g>
        <g class="straw-b">
          <g fill="#603813">
            <rect x="28" y="18" width="1" height="1" />
            <rect x="29" y="20" width="1" height="2" />
            <rect x="31" y="23" width="1" height="1" />
            <rect x="19" y="24" width="2" height="1" />
          </g>
          <g fill="#bd8333">
            <rect x="26" y="18" width="1" height="1" />
            <rect x="31" y="18" width="1" height="1" />
            <rect x="23" y="19" width="1" height="1" />
            <rect x="28" y="19" width="1" height="1" />
            <rect x="25" y="20" width="1" height="1" />
            <rect x="21" y="21" width="1" height="4" />
            <rect x="24" y="21" width="2" height="1" />
            <rect x="28" y="21" width="1" height="1" />
            <rect x="19" y="22" width="1" height="2" />
            <rect x="31" y="22" width="1" height="1" />
            <rect x="26" y="23" width="1" height="1" />
            <rect x="23" y="24" width="1" height="1" />
            <rect x="29" y="24" width="1" height="1" />
            <rect x="22" y="25" width="1" height="1" />
            <rect x="26" y="25" width="1" height="1" />
          </g>
          <g fill="#efb154">
            <rect x="27" y="18" width="1" height="1" />
            <rect x="24" y="19" width="1" height="1" />
            <rect x="26" y="19" width="2" height="1" />
            <rect x="22" y="20" width="1" height="1" />
            <rect x="28" y="20" width="1" height="1" />
            <rect x="23" y="21" width="1" height="1" />
            <rect x="26" y="21" width="2" height="1" />
            <rect x="20" y="22" width="1" height="2" />
            <rect x="25" y="22" width="1" height="1" />
            <rect x="28" y="22" width="1" height="1" />
            <rect x="30" y="22" width="1" height="1" />
            <rect x="22" y="23" width="1" height="2" />
            <rect x="24" y="23" width="2" height="1" />
            <rect x="27" y="23" width="1" height="1" />
            <rect x="29" y="23" width="2" height="1" />
            <rect x="27" y="24" width="2" height="1" />
            <rect x="24" y="25" width="2" height="1" />
          </g>
          <g fill="#f4db9a">
            <rect x="25" y="19" width="1" height="1" />
            <rect x="23" y="20" width="2" height="1" />
            <rect x="26" y="20" width="2" height="1" />
            <rect x="22" y="21" width="1" height="1" />
            <rect x="22" y="22" width="3" height="1" />
            <rect x="26" y="22" width="2" height="1" />
            <rect x="29" y="22" width="1" height="1" />
            <rect x="23" y="23" width="1" height="1" />
            <rect x="28" y="23" width="1" height="1" />
            <rect x="24" y="24" width="3" height="1" />
            <rect x="23" y="25" width="1" height="1" />
          </g>
        </g>
        <!-- 两侧短翼 -->
        <g class="wing-l">
          <g fill="#d97757">
            <rect x="4" y="16" width="2" height="2" />
          </g>
        </g>
        <g class="wing-r">
          <g fill="#d97757">
            <rect x="17" y="14" width="1" height="3" />
          </g>
          <g fill="#bd674d">
            <rect x="18" y="14" width="1" height="3" />
          </g>
        </g>
        <!-- 短腿两帧 -->
        <g class="leg-a">
          <g fill="#d97757">
            <rect x="6" y="21" width="2" height="1" />
            <rect x="14" y="21" width="2" height="1" />
          </g>
        </g>
        <g class="leg-b">
          <g fill="#d97757">
            <rect x="10" y="21" width="2" height="1" />
          </g>
          <g fill="#bd674d">
            <rect x="17" y="21" width="1" height="1" />
          </g>
        </g>
        <!-- 帽身、身体、扫帚杆 -->
        <g class="hat" fill="#2f2f2d">
          <rect x="10" y="7" width="5" height="1" />
          <rect x="9" y="8" width="6" height="2" />
          <rect x="8" y="10" width="7" height="1" />
          <rect x="7" y="11" width="10" height="1" />
          <rect x="3" y="12" width="17" height="1" />
          <rect x="4" y="13" width="2" height="1" />
          <rect x="17" y="13" width="2" height="1" />
        </g>
        <g fill="#d97757">
          <rect x="6" y="14" width="2" height="2" />
          <rect x="9" y="14" width="5" height="2" />
          <rect x="15" y="14" width="2" height="2" />
          <rect x="7" y="16" width="10" height="1" />
          <rect x="7" y="17" width="9" height="1" />
          <rect x="6" y="18" width="10" height="2" />
          <rect x="6" y="20" width="2" height="1" />
          <rect x="10" y="20" width="2" height="1" />
          <rect x="14" y="20" width="1" height="1" />
        </g>
        <g fill="#bd674d">
          <rect x="6" y="13" width="11" height="1" />
          <rect x="8" y="14" width="1" height="2" />
          <rect x="14" y="14" width="1" height="2" />
          <rect x="6" y="16" width="1" height="2" />
          <rect x="16" y="17" width="1" height="3" />
          <rect x="8" y="20" width="2" height="1" />
          <rect x="12" y="20" width="2" height="1" />
          <rect x="15" y="20" width="3" height="1" />
        </g>
        <g fill="#603813">
          <rect x="1" y="20" width="2" height="1" />
          <rect x="3" y="21" width="3" height="1" />
          <rect x="5" y="22" width="14" height="1" />
        </g>
        <g fill="#2f1800">
          <rect x="0" y="20" width="1" height="1" />
          <rect x="1" y="21" width="2" height="1" />
          <rect x="3" y="22" width="2" height="1" />
          <rect x="7" y="23" width="12" height="1" />
        </g>
        <!-- 眼睛 -->
        <g class="eyes">
          <g fill="#000000">
            <rect x="7" y="14" width="1" height="2" />
            <rect x="13" y="14" width="1" height="2" />
          </g>
        </g>
      </g>
    </g>
  </svg>
</template>

<style scoped>
/* Decorative mascot for the redeem card. Inline (not an <img>) so the sky can follow the site theme. */
.moon {
  display: none;
}
:root[data-theme='dark'] .sun {
  display: none;
}
:root[data-theme='dark'] .moon {
  display: inline;
}
/* The near-black hat would sink into the dark card; a slate grey still reads as a black hat. */
:root[data-theme='dark'] .hat {
  fill: #4a4d57;
}

/* Whole rider bobs and tilts; hat tip, straw, wings and legs swap between two pixel frames. */
.rider {
  animation: fly-ride 2.6s ease-in-out infinite;
  transform-origin: 120px 125px;
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
.wing-l {
  animation: flap-up 0.56s step-end infinite;
}
.wing-r {
  animation: flap-down 0.56s step-end infinite;
}
.leg-a {
  animation: frame-a 0.56s step-end infinite;
}
.leg-b {
  animation: frame-b 0.56s step-end infinite;
}
.spark-1 {
  animation: spark-stream 0.9s linear infinite;
}
.spark-2 {
  animation: spark-stream 0.9s linear 0.3s infinite;
}
.spark-3 {
  animation: spark-stream 0.9s linear 0.6s infinite;
}
.speed-line {
  animation: warp-speed 1.4s linear infinite;
}
.speed-line-late {
  animation: warp-speed 1.4s linear 0.7s infinite;
}
.star-1,
.sun-glint {
  animation: twinkle 2.2s step-end infinite;
}
.star-2 {
  animation: twinkle 2.2s step-end 1.1s infinite;
}
/* Blink: the two-cell-tall eyes squash to one cell. */
.eyes {
  animation: blink 4s step-end infinite;
  transform-origin: 0 16px;
}

@keyframes fly-ride {
  0%,
  100% {
    transform: translate(0, 0) rotate(1deg);
  }
  50% {
    transform: translate(-4px, -9px) rotate(4deg);
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
@keyframes flap-up {
  0% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-1px);
  }
}
@keyframes flap-down {
  0% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(1px);
  }
}
@keyframes spark-stream {
  0% {
    transform: translate(0, 0);
    opacity: 0.95;
  }
  100% {
    transform: translate(36px, 14px);
    opacity: 0;
  }
}
@keyframes warp-speed {
  0% {
    transform: translateX(-40px);
    opacity: 0;
  }
  40% {
    opacity: 0.45;
  }
  100% {
    transform: translateX(70px);
    opacity: 0;
  }
}
@keyframes twinkle {
  0% {
    opacity: 0.25;
  }
  50% {
    opacity: 0.8;
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
  .wing-l,
  .wing-r,
  .leg-a,
  .spark-1,
  .spark-2,
  .spark-3,
  .speed-line,
  .speed-line-late,
  .star-1,
  .star-2,
  .sun-glint,
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
