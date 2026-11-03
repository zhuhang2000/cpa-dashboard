import { reactive } from 'vue'
import { settingsApi } from '@/api/settings'

export const siteStore = reactive({
  status: null, // site info from /api/status
  get siteName() {
    return this.status?.site_name || 'API 控制台'
  },
})

let statusPromise = null
export function ensureStatus() {
  if (siteStore.status) return Promise.resolve(siteStore.status)
  if (!statusPromise) {
    statusPromise = settingsApi
      .getStatus()
      .then((data) => (siteStore.status = data))
      .catch(() => {
        statusPromise = null
        siteStore.status = {
          site_name: 'API 控制台',
          currency_symbol: '$',
          allow_register: true,
          payment: { online: false, channels: [], presets: [] },
        }
        return siteStore.status
      })
  }
  return statusPromise
}

export async function refreshStatus() {
  statusPromise = null
  siteStore.status = null
  return ensureStatus()
}
