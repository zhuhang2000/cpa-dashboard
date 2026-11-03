import { createRouter, createWebHistory } from 'vue-router'
import { setUnauthorizedHandler } from '@/api/http'
import { Role } from '@/constants'
import { canOpen, ensureStatus, ensureUser, store } from '@/stores'
import { routes } from './routes'

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
  if (!canOpen(to.meta)) return { path: store.user?.role === Role.MANAGER ? '/admin/users' : '/' }
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
