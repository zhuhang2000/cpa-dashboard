<template>
  <div class="layout" :class="{ 'nav-open': navOpen }">
    <aside class="sidebar">
      <RouterLink to="/" class="brand">
        <span class="brand-logo"><Icon name="logo" :size="19" :stroke="2.4" /></span>
        <span class="truncate">{{ siteName }}</span>
      </RouterLink>
      <nav class="nav" @click="navOpen = false">
        <div class="nav-section">控制台</div>
        <RouterLink v-for="item in mainNav" :key="item.to" :to="item.to" class="nav-link">
          <Icon :name="item.icon" :size="18" />
          {{ item.label }}
        </RouterLink>
        <template v-if="isAdmin">
          <div class="nav-section">管理后台</div>
          <RouterLink v-for="item in adminNav" :key="item.to" :to="item.to" class="nav-link">
            <Icon :name="item.icon" :size="18" />
            {{ item.label }}
          </RouterLink>
        </template>
      </nav>
      <div class="sidebar-foot">
        <span>{{ store.user?.username }}</span>
        <span>v{{ store.status?.version || '1.0' }}</span>
      </div>
    </aside>
    <div class="backdrop" @click="navOpen = false" />

    <div class="main">
      <header class="topbar">
        <button class="btn btn-ghost btn-icon menu-btn" aria-label="打开菜单" @click="navOpen = !navOpen">
          <Icon name="menu" />
        </button>
        <div class="topbar-title truncate">{{ route.meta.title }}</div>
        <div class="topbar-right">
          <RouterLink to="/recharge" class="balance-pill num" :class="{ low: lowBalance }" title="账户余额，点击充值">
            <Icon name="wallet" :size="16" />
            {{ money(store.user?.balance || 0) }}
          </RouterLink>
          <button class="btn btn-ghost btn-icon" :title="themeLabel" :aria-label="themeLabel" @click="toggleTheme">
            <Icon :name="isDark ? 'sun' : 'moon'" />
          </button>
          <div ref="menuRef" class="dropdown">
            <button class="user-btn" aria-label="用户菜单" aria-haspopup="menu" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen">
              <span class="avatar">{{ initial }}</span>
              <span class="hide-sm">{{ store.user?.username }}</span>
              <Icon name="chevron-down" :size="16" class="hide-sm" />
            </button>
            <div v-if="menuOpen" class="dropdown-menu" role="menu" @click="menuOpen = false">
              <div class="dropdown-head">
                <div style="font-weight: 600">{{ store.user?.username }}</div>
                <div class="muted" style="font-size: 12.5px">
                  {{ store.user?.email || (isAdmin ? '管理员' : '普通用户') }}
                </div>
              </div>
              <RouterLink to="/settings" class="dropdown-item"><Icon name="user" :size="16" />个人设置</RouterLink>
              <RouterLink to="/recharge" class="dropdown-item"><Icon name="wallet" :size="16" />充值中心</RouterLink>
              <button class="dropdown-item danger" @click="doLogout"><Icon name="logout" :size="16" />退出登录</button>
            </div>
          </div>
        </div>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from './Icon.vue'
import { effectiveTheme, logout, refreshUser, store, toggleTheme } from '../store'
import { money } from '../format'

const route = useRoute()
const router = useRouter()
const navOpen = ref(false)
const menuOpen = ref(false)
const menuRef = ref(null)

const mainNav = [
  { to: '/', label: '概览', icon: 'grid' },
  { to: '/keys', label: 'API 密钥', icon: 'key' },
  { to: '/usage', label: '用量明细', icon: 'activity' },
  { to: '/recharge', label: '充值中心', icon: 'wallet' },
  { to: '/pricing', label: '模型价格', icon: 'tag' },
  { to: '/settings', label: '个人设置', icon: 'settings' },
]
const adminNav = [
  { to: '/admin', label: '运营概况', icon: 'trend' },
  { to: '/admin/users', label: '用户管理', icon: 'users' },
  { to: '/admin/codes', label: '兑换码', icon: 'ticket' },
  { to: '/admin/prices', label: '模型定价', icon: 'coins' },
  { to: '/admin/settings', label: '系统设置', icon: 'sliders' },
]

const siteName = computed(() => store.status?.site_name || 'API 控制台')
const isAdmin = computed(() => store.user?.role === 'admin')
const initial = computed(() => (store.user?.username || '?').slice(0, 1).toUpperCase())
const lowBalance = computed(() => (store.user?.balance ?? 1) <= 0)
const isDark = computed(() => (store.theme, effectiveTheme() === 'dark'))
const themeLabel = computed(() => (isDark.value ? '切换到浅色模式' : '切换到深色模式'))

// Keep the balance pill fresh while navigating.
watch(
  () => route.fullPath,
  () => {
    navOpen.value = false
    refreshUser({ throttle: 8000 })
  },
)

function onDocClick(e) {
  if (menuOpen.value && menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

async function doLogout() {
  await logout()
  router.replace('/login')
}
</script>
