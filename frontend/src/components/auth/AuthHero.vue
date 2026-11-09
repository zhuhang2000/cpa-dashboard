<template>
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
</template>

<script setup>
import AuthArt from './AuthArt.vue'
import Icon from '@/components/base/Icon.vue'

const points = [
  { icon: 'zap', title: '随时满血', desc: '不用等，不降智' },
  { icon: 'coins', title: '官方同价', desc: '充 1 元当 1 美元用' },
  { icon: 'wallet', title: '余额不过期', desc: '用多少扣多少' },
]
</script>
