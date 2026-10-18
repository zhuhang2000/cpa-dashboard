import { createRouter, createWebHistory } from 'vue-router'
import { setUnauthorizedHandler } from './api'
import { Role } from './constants'
import { ensureStatus, ensureUser, store } from './store'
import AppLayout from '@/layouts/AppLayout.vue'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Dashboard from '@/views/Dashboard.vue'

// Pages inside the app layout, one list per sidebar section. AppLayout builds the menu from
// these routes, so a page with an `icon` only needs its entry here to appear in the sidebar.
const consolePages = [
  { path: '', component: Dashboard, meta: { title: '概览', icon: 'grid' } },
  { path: 'keys', component: () => import('@/views/Keys.vue'), meta: { title: 'API 密钥', icon: 'key' } },
  { path: 'usage', component: () => import('@/views/Usage.vue'), meta: { title: '用量明细', icon: 'activity' } },
  { path: 'recharge', component: () => import('@/views/Recharge.vue'), meta: { title: '充值中心', icon: 'wallet' } },
  { path: 'pricing', component: () => import('@/views/Pricing.vue'), meta: { title: '模型价格', icon: 'tag' } },
  { path: 'settings', component: () => import('@/views/Settings.vue'), meta: { title: '个人设置', icon: 'settings' } },
]
const adminPages = [
  { path: '', component: () => import('@/views/admin/Overview.vue'), meta: { title: '运营概况', icon: 'trend' } },
  { path: 'users', component: () => import('@/views/admin/Users.vue'), meta: { title: '用户管理', icon: 'users' } },
  { path: 'codes', component: () => import('@/views/admin/Codes.vue'), meta: { title: '兑换码', icon: 'ticket' } },
  { path: 'prices', component: () => import('@/views/admin/Prices.vue'), meta: { title: '模型定价', icon: 'coins' } },
  {
    path: 'settings',
    component: () => import('@/views/admin/Settings.vue'),
    meta: { title: '系统设置', icon: 'sliders' },
  },
]

const routes = [
  { path: '/login', component: Login, meta: { title: '登录', guest: true } },
  { path: '/register', component: Register, meta: { title: '注册', guest: true } },
  {
    path: '/',
    component: AppLayout,
    meta: { auth: true },
    // One component-less group per sidebar section. Route meta is merged from parent to child,
    // so `admin: true` here covers every admin page in the guard below.
    children: [
      { path: '', meta: { section: '控制台' }, children: consolePages },
      { path: 'admin', meta: { section: '管理后台', admin: true }, children: adminPages },
    ],
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFound.vue'), meta: { title: '页面不存在' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  await ensureStatus()
  const needsAuth = to.matched.some((r) => r.meta.auth)
  if (needsAuth || to.meta.guest) await ensureUser()
  if (needsAuth && !store.user) {
    return { path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  if (to.meta.guest && store.user) return { path: '/' }
  if (to.meta.admin && store.user?.role !== Role.ADMIN) return { path: '/' }
  return true
})

router.afterEach((to) => {
  const site = store.status?.site_name || 'API 控制台'
  document.title = to.meta.title ? `${to.meta.title} · ${site}` : site
})

// Session expired mid-use: drop the user and go to the login page.
setUnauthorizedHandler(() => {
  if (!store.user) return
  store.user = null
  const current = router.currentRoute.value
  if (!current.meta.guest) router.replace({ path: '/login', query: { redirect: current.fullPath } })
})

export default router
