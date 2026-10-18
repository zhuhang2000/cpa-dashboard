<template>
  <div class="auth theme-light">
    <section class="auth-brand">
      <div class="auth-logo">
        <span class="brand-logo"><Icon name="logo" :size="20" :stroke="2.4" /></span>
        {{ siteName }}
      </div>
      <div class="auth-hero">
        <h2>一个密钥，接入主流大模型</h2>
        <p>按量计费 · 用量透明 · 额度可控</p>
        <AuthArt class="auth-art" />
      </div>
      <div class="auth-copy">© {{ year }} {{ siteName }}</div>
    </section>
    <section class="auth-panel">
      <div class="auth-card">
        <div class="auth-mobile-logo">
          <span class="brand-logo"><Icon name="logo" :size="20" :stroke="2.4" /></span>
          {{ siteName }}
        </div>
        <slot />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AuthArt from './AuthArt.vue'
import Icon from '@/components/Icon.vue'
import { store } from '@/store'

const siteName = computed(() => store.status?.site_name || 'API 控制台')
const year = new Date().getFullYear()
</script>
