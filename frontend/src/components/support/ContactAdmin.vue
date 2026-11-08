<template>
  <div class="contact">
    <div v-if="contactAdmin.open" ref="contactPanel" class="contact-panel card" role="dialog" aria-label="联系管理员">
      <div class="contact-head">
        <div>
          <div class="card-title">联系管理员</div>
          <div class="contact-sub">充值或使用中遇到问题，都可以找我们</div>
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
  display: flex;
  align-items: center;
  gap: 12px;
  transform: translateY(-50%);
}
.contact-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  border: 1px solid transparent;
  border-right: 0;
  border-radius: 10px 0 0 10px;
  background: var(--accent);
  color: var(--on-accent);
  box-shadow: var(--shadow-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.contact-tab:hover {
  background: var(--accent-hover);
}
:root[data-theme='dark'] .contact-tab {
  background: #262420;
  border-color: #3a3630;
  color: #d6d0c4;
  box-shadow: var(--shadow);
}
:root[data-theme='dark'] .contact-tab:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--on-accent);
}
.contact-tab span {
  writing-mode: vertical-rl;
  letter-spacing: 2px;
}
.contact-panel {
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
.contact-sub {
  margin-top: 2px;
  font-size: 12.5px;
  color: var(--muted);
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
