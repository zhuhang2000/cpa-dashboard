import AppLayout from '@/layouts/AppLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import Dashboard from '@/views/Dashboard.vue'

// Pages inside the app layout, one list per sidebar section. AppLayout builds the menu from
// these routes, so a page with an `icon` only needs its entry here to appear in the sidebar.
const consolePages = [
  { path: '', component: Dashboard, meta: { title: '概览', icon: 'grid' } },
  { path: 'keys', component: () => import('@/views/Keys.vue'), meta: { title: 'API 密钥', icon: 'key' } },
  { path: 'usage', component: () => import('@/views/Usage.vue'), meta: { title: '用量明细', icon: 'activity' } },
  {
    path: 'recharge',
    component: () => import('@/views/recharge/index.vue'),
    meta: { title: '充值中心', icon: 'wallet' },
  },
  { path: 'pricing', component: () => import('@/views/Pricing.vue'), meta: { title: '模型价格', icon: 'tag' } },
  { path: 'settings', component: () => import('@/views/Settings.vue'), meta: { title: '个人设置', icon: 'settings' } },
]
// `staff: true` opens a page to tag managers as well (see canOpen in stores/index.js).
const adminPages = [
  { path: '', component: () => import('@/views/admin/Overview.vue'), meta: { title: '运营概况', icon: 'trend' } },
  {
    path: 'users',
    component: () => import('@/views/admin/Users.vue'),
    meta: { title: '用户管理', icon: 'users', staff: true },
  },
  { path: 'codes', component: () => import('@/views/admin/Codes.vue'), meta: { title: '兑换码', icon: 'ticket' } },
  { path: 'prices', component: () => import('@/views/admin/Prices.vue'), meta: { title: '模型定价', icon: 'coins' } },
  {
    path: 'settings',
    component: () => import('@/views/admin/Settings.vue'),
    meta: { title: '系统设置', icon: 'sliders' },
  },
]

export const routes = [
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
  // Keep the console's root route first; this layout only hosts /login and /register.
  {
    path: '/',
    component: AuthLayout,
    meta: { guest: true },
    children: [
      { path: 'login', component: Login, meta: { title: '登录' } },
      { path: 'register', component: Register, meta: { title: '注册' } },
    ],
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFound.vue'), meta: { title: '页面不存在' } },
]
