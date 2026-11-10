<template>
  <div class="contact">
    <div v-if="contactAdmin.open" ref="contactPanel" class="contact-panel card" role="dialog" aria-label="联系管理员">
      <div class="contact-head">
        <div>
          <div class="card-title">联系管理员</div>
          <div class="card-sub">充值或使用中遇到问题，都可以找我们</div>
        </div>
        <button class="btn btn-ghost btn-icon btn-sm" aria-label="关闭" @click="contactAdmin.close()">
          <Icon name="x" :size="16" />
        </button>
      </div>
      <figure class="contact-qr">
        <img :src="wechatQr" alt="管理员微信二维码" width="180" height="180" />
        <figcaption>打开微信「扫一扫」添加管理员</figcaption>
      </figure>
    </div>
    <button class="contact-tab" data-tour="contact" :aria-expanded="contactAdmin.open" @click="contactAdmin.toggle">
      <Icon name="message" :size="18" />
      <span>联系管理员</span>
    </button>
  </div>
</template>

<script>
import { ref } from 'vue'
import { usePopover } from '@/composables/usePopover'

// One contact panel for the whole app (AppLayout mounts a single ContactAdmin). Besides the side tab, other
// screens open it from their own trigger with `@click="contactAdmin.toggle"`, e.g. the redeem card's bubble.
const contactPanel = ref(null)
export const contactAdmin = usePopover({ panel: contactPanel })
</script>

<script setup>
import wechatQr from '@/assets/wechat-qr.jpg'
import Icon from '@/components/base/Icon.vue'
</script>

<style scoped>
.contact {
  position: fixed;
  top: 50%;
  right: 0;
  z-index: 32;
  transform: translateY(-50%);
}
.contact-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  border: 0;
  border-radius: 10px 0 0 10px;
  background: var(--accent);
  color: var(--on-accent);
  box-shadow: var(--shadow-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transform-origin: right center; /* 按下时朝屏幕边缘缩 */
  /* 缩回稍慢，不显突兀 */
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    padding-right 0.28s cubic-bezier(0.25, 1, 0.5, 1),
    transform 0.2s ease;
}
/* 悬停探出要快；面板打开期间也保持探出 + 高亮 */
.contact-tab:hover,
.contact-tab[aria-expanded='true'] {
  background-color: var(--accent-hover);
  padding-right: 24px;
  transition:
    background-color 0.15s ease-out,
    color 0.15s ease-out,
    padding-right 0.18s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); /* 松手回弹 */
}
/* 按下：瞬间压暗、缩小；须写在 :hover 之后才能覆盖 */
.contact-tab:active {
  background-color: var(--accent-active);
  transform: scale(0.9);
}
:root[data-theme='dark'] .contact-tab {
  background: #24221e;
  color: #c4beb5;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}
:root[data-theme='dark'] .contact-tab:hover,
:root[data-theme='dark'] .contact-tab[aria-expanded='true'] {
  background: #1c1a17;
  color: var(--text);
}
.contact-tab span {
  writing-mode: vertical-rl;
  letter-spacing: 2px;
}
.contact-panel {
  position: absolute;
  right: calc(100% + 12px); /* 靠在按钮左侧，保持 12px 间距 */
  top: 50%; /* 垂直对齐按钮中心 */
  transform: translateY(-50%);
  width: min(300px, calc(100vw - 72px));
  padding: 16px;
  box-shadow: var(--shadow-lg);
}
.contact-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.contact-qr {
  margin: 0;
  text-align: center;
}
/* Keep the white quiet zone in dark mode too, or phones can't scan it. */
.contact-qr img {
  display: block;
  margin: 0 auto;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #fff;
}
.contact-qr figcaption {
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--muted);
}
</style>
