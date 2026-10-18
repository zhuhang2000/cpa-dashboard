import { reactive } from 'vue'
import { api } from './api'

export const store = reactive({
  status: null, // site info from /api/status
  user: null,
  userLoaded: false,
  keyCount: 0,
  theme: readTheme(),
})

function readTheme() {
  try {
    return localStorage.getItem('portal-theme') || 'system'
  } catch {
    return 'system'
  }
}

let statusPromise = null
export function ensureStatus() {
  if (store.status) return Promise.resolve(store.status)
  if (!statusPromise) {
    statusPromise = api
      .get('/api/status')
      .then((data) => (store.status = data))
      .catch(() => {
        statusPromise = null
        store.status = {
          site_name: 'API 控制台',
          currency_symbol: '$',
          allow_register: true,
          payment: { online: false, channels: [], presets: [] },
        }
        return store.status
      })
  }
  return statusPromise
}

export async function refreshStatus() {
  statusPromise = null
  store.status = null
  return ensureStatus()
}

export async function ensureUser() {
  if (store.userLoaded) return store.user
  return refreshUser()
}

let lastRefresh = 0
export async function refreshUser({ throttle = 0 } = {}) {
  if (throttle && Date.now() - lastRefresh < throttle) return store.user
  lastRefresh = Date.now()
  try {
    const data = await api.get('/api/user/me', null, { silent401: true })
    store.user = data.user || null
    store.keyCount = data.key_count || 0
  } catch (e) {
    if (e.status === 401) store.user = null
    else if (!store.userLoaded) store.user = null
  }
  store.userLoaded = true
  return store.user
}

export function setUser(user) {
  store.user = user
  store.userLoaded = true
}

export async function logout() {
  try {
    await api.post('/api/auth/logout')
  } catch {
    /* ignore */
  }
  store.user = null
  store.userLoaded = true
}

export function effectiveTheme() {
  if (store.theme === 'light' || store.theme === 'dark') return store.theme
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function toggleTheme() {
  const next = effectiveTheme() === 'dark' ? 'light' : 'dark'
  store.theme = next
  document.documentElement.setAttribute('data-theme', next)
  try {
    localStorage.setItem('portal-theme', next)
  } catch {
    /* ignore */
  }
}
