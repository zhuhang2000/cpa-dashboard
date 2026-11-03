<template>
  <div class="auth theme-light">
    <section class="auth-brand">
      <div class="auth-logo">
        <span class="brand-logo"><Icon name="logo" :size="20" :stroke="2.4" /></span>
        {{ siteName }}
      </div>
      <div class="auth-hero">
        <span class="auth-eyebrow"><Icon name="zap" :size="14" />订阅额度的备用电源</span>
        <h2>你的 <span class="auth-highlight">AI 充电宝</span></h2>
        <p>订阅限额又降智？接上 API，满血接着用。</p>
        <AuthArt class="auth-art" />
        <ul class="auth-points">
          <li v-for="point in points" :key="point.title">
            <span class="auth-point-icon"><Icon :name="point.icon" :size="16" /></span>
            <div>
              <div class="auth-point-title">{{ point.title }}</div>
              <div class="auth-point-desc">{{ point.desc }}</div>
            </div>
          </li>
        </ul>
      </div>
      <div class="auth-copy">© {{ year }} {{ siteName }}</div>
    </section>
    <section class="auth-panel">
      <div class="auth-card">
        <div class="auth-mobile-logo">
          <span class="brand-logo"><Icon name="logo" :size="20" :stroke="2.4" /></span>
          {{ siteName }}
        </div>
        <RouterView />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AuthArt from '@/components/auth/AuthArt.vue'
import Icon from '@/components/base/Icon.vue'
import { store } from '@/stores'

const siteName = computed(() => store.status?.site_name || 'API 控制台')
const year = new Date().getFullYear()

const points = [
  { icon: 'zap', title: '随时满血', desc: '不用等，不降智' },
  { icon: 'coins', title: '官方同价', desc: '充 1 元当 1 美元用' },
  { icon: 'wallet', title: '余额不过期', desc: '用多少扣多少' },
]
</script>
