<template>
  <div class="auth theme-light">
    <section class="auth-brand">
      <div class="auth-logo">
        <span class="brand-logo"><Icon name="logo" :size="20" :stroke="2.4" /></span>
        {{ siteStore.siteName }}
      </div>
      <AuthHero />
      <div class="auth-copy">© {{ year }} {{ siteStore.siteName }}</div>
    </section>
    <section class="auth-panel">
      <div class="auth-card">
        <div class="auth-mobile-logo">
          <span class="brand-logo"><Icon name="logo" :size="20" :stroke="2.4" /></span>
          {{ siteStore.siteName }}
        </div>
        <RouterView />
      </div>
    </section>
  </div>
</template>

<script setup>
import AuthHero from '@/components/auth/AuthHero.vue'
import Icon from '@/components/base/Icon.vue'
import { siteStore } from '@/stores'

const year = new Date().getFullYear()
</script>
