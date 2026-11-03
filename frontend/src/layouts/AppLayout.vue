<template>
  <div class="layout" :class="{ 'nav-open': navOpen }">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-logo"><Icon name="logo" :size="19" :stroke="2.4" /></span>
        <span class="truncate">{{ siteStore.siteName }}</span>
      </div>
      <nav class="nav" @click="navOpen = false">
        <template v-for="section in sections" :key="section.label">
          <div class="nav-section">{{ section.label }}</div>
          <RouterLink v-for="item in section.items" :key="item.to" :to="item.to" class="nav-link">
            <Icon :name="item.icon" :size="18" />
            {{ item.label }}
          </RouterLink>
        </template>
      </nav>
    </aside>
    <div class="backdrop" @click="navOpen = false" />

    <div class="main">
      <header class="topbar">
        <button class="btn btn-ghost btn-icon menu-btn" aria-label="打开菜单" @click="navOpen = !navOpen">
          <Icon name="menu" />
        </button>
        <div class="topbar-title truncate">{{ route.meta.title }}</div>
        <div class="topbar-right">
          <RouterLink to="/billing" class="balance-pill num" :class="{ low: lowBalance }" title="账户余额，点击充值">
            <Icon name="wallet" :size="16" />
            {{ money(sessionStore.user?.balance || 0) }}
          </RouterLink>
          <GuideTour />
          <NoticeBell />
          <button class="btn btn-ghost btn-icon" :title="themeLabel" :aria-label="themeLabel" @click="toggleTheme">
            <Icon :name="isDark ? 'moon' : 'sun'" />
          </button>
          <div class="dropdown">
            <button
              class="user-btn"
              aria-label="用户菜单"
              aria-haspopup="menu"
              :aria-expanded="userMenu.open"
              @click="userMenu.toggle"
            >
              <span class="avatar">{{ initial }}</span>
              <span class="hide-sm">{{ sessionStore.user?.username }}</span>
              <Icon name="chevron-down" :size="16" class="hide-sm" />
            </button>
            <div v-if="userMenu.open" ref="userMenuPanel" class="dropdown-menu" role="menu" @click="userMenu.close()">
              <div class="dropdown-head">
                <div style="font-weight: 600">{{ sessionStore.user?.username }}</div>
                <div class="muted" style="font-size: 12.5px">
                  {{ sessionStore.user?.email || ROLES[sessionStore.role]?.label }}
                </div>
              </div>
              <RouterLink to="/settings" class="dropdown-item"><Icon name="user" :size="16" />个人设置</RouterLink>
              <RouterLink to="/billing" class="dropdown-item"><Icon name="wallet" :size="16" />充值中心</RouterLink>
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
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ContactAdmin from '@/components/support/ContactAdmin.vue'
import GuideTour from '@/components/onboarding/GuideTour.vue'
import Icon from '@/components/base/Icon.vue'
import NoticeBell from '@/components/notices/NoticeBell.vue'
import { usePopover } from '@/composables/usePopover'
import { ROLES } from '@/constants'
import { canOpen, themeStore, logout, refreshUser, siteStore, sessionStore, toggleTheme } from '@/stores'
import { money } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const navOpen = ref(false)
const userMenuPanel = ref(null)
const userMenu = usePopover({ panel: userMenuPanel })

// 加载当前用户可见的侧边栏组件
const sections = computed(() =>
  route.matched[0].children
    .map((group) => ({
      label: group.meta.section,
      items: group.children
        .filter((page) => page.meta.icon && canOpen({ ...group.meta, ...page.meta }))
        .map((page) => ({
          to: `/${[group.path, page.path].filter(Boolean).join('/')}`,
          label: page.meta.title,
          icon: page.meta.icon,
        })),
    }))
    .filter((section) => section.items.length),
)
const initial = computed(() => (sessionStore.user?.username || '?').slice(0, 1).toUpperCase())
const lowBalance = computed(() => (sessionStore.user?.balance ?? 1) <= 0)
const isDark = computed(() => themeStore.theme === 'dark')
const themeLabel = computed(() => (isDark.value ? '切换到浅色模式' : '切换到深色模式'))

watch(
  () => route.fullPath,
  () => {
    navOpen.value = false
    refreshUser({ throttle: 8000 })
  },
)

async function doLogout() {
  await logout()
  router.replace('/login')
}
</script>
