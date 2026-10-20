<template>
  <div class="layout" :class="{ 'nav-open': navOpen }">
    <aside class="sidebar">
      <RouterLink to="/" class="brand">
        <span class="brand-logo"><Icon name="logo" :size="19" :stroke="2.4" /></span>
        <span class="truncate">{{ siteName }}</span>
      </RouterLink>
      <nav class="nav" @click="navOpen = false">
        <template v-for="section in sections" :key="section.label">
          <div class="nav-section">{{ section.label }}</div>
          <RouterLink v-for="item in section.items" :key="item.to" :to="item.to" class="nav-link">
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
        <WelcomeMarquee />
        <div class="topbar-right">
          <RouterLink to="/recharge" class="balance-pill num" :class="{ low: lowBalance }" title="账户余额，点击充值">
            <Icon name="wallet" :size="16" />
            {{ money(store.user?.balance || 0) }}
          </RouterLink>
          <button class="btn btn-ghost btn-icon" :title="themeLabel" :aria-label="themeLabel" @click="toggleTheme">
            <Icon :name="isDark ? 'sun' : 'moon'" />
          </button>
          <div ref="menuRef" class="dropdown">
            <button
              class="user-btn"
              aria-label="用户菜单"
              aria-haspopup="menu"
              :aria-expanded="menuOpen"
              @click="menuOpen = !menuOpen"
            >
              <span class="avatar">{{ initial }}</span>
              <span class="hide-sm">{{ store.user?.username }}</span>
              <Icon name="chevron-down" :size="16" class="hide-sm" />
            </button>
            <div v-if="menuOpen" class="dropdown-menu" role="menu" @click="menuOpen = false">
              <div class="dropdown-head">
                <div style="font-weight: 600">{{ store.user?.username }}</div>
                <div class="muted" style="font-size: 12.5px">
                  {{ store.user?.email || ROLES[store.user?.role]?.label }}
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
    <ContactAdmin />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ContactAdmin from '@/components/ContactAdmin.vue'
import Icon from '@/components/Icon.vue'
import WelcomeMarquee from '@/components/WelcomeMarquee.vue'
import { ROLES, Role } from '@/constants'
import { effectiveTheme, logout, refreshUser, store, toggleTheme } from '@/store'
import { money } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const navOpen = ref(false)
const menuOpen = ref(false)
const menuRef = ref(null)

const siteName = computed(() => store.status?.site_name || 'API 控制台')
const isAdmin = computed(() => store.user?.role === Role.ADMIN)

// The sidebar mirrors the route table in router.js: each child group of this layout's route is a
// section listing its pages that have an icon. Admin groups are shown to admins only.
const sections = computed(() =>
  route.matched[0].children
    .filter((group) => !group.meta.admin || isAdmin.value)
    .map((group) => ({
      label: group.meta.section,
      items: group.children
        .filter((page) => page.meta.icon)
        .map((page) => ({
          to: `/${[group.path, page.path].filter(Boolean).join('/')}`,
          label: page.meta.title,
          icon: page.meta.icon,
        })),
    })),
)
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
