import { reactive } from 'vue'
import { accountsApi } from '@/api/accounts'
import { Role } from '@/constants'

export const sessionStore = reactive({
  user: null,
  keyCount: 0,

  get role() {
    return this.user?.role ?? null
  },

  get isAdmin() {
    return this.role === Role.ADMIN
  },

  get isManager() {
    return this.role === Role.MANAGER
  },
})

let userLoaded = false
export async function ensureUser() {
  if (userLoaded) return sessionStore.user
  return refreshUser()
}

let lastRefresh = 0
export async function refreshUser({ throttle = 0 } = {}) {
  if (throttle && Date.now() - lastRefresh < throttle) return sessionStore.user
  lastRefresh = Date.now()
  try {
    const data = await accountsApi.getMe()
    sessionStore.user = data.user || null
    sessionStore.keyCount = data.key_count || 0
  } catch (e) {
    if (e.status === 401) sessionStore.user = null
    else if (!userLoaded) sessionStore.user = null
  }
  userLoaded = true
  return sessionStore.user
}

export function setUser(user) {
  sessionStore.user = user
  userLoaded = true
}

export function canOpen(meta) {
  if (!meta.admin) return true
  return sessionStore.isAdmin || (sessionStore.isManager && Boolean(meta.staff))
}

export async function logout() {
  try {
    await accountsApi.logout()
  } catch {
    /* ignore */
  }
  sessionStore.user = null
  userLoaded = true
}
