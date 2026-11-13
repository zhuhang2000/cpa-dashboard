import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { noticesApi } from '@/api/notices'
import { settingsApi } from '@/api/settings'
import { siteStore, sessionStore } from '@/stores'
import { toast } from '@/toast'

// One controller per bell. Dialogs can unmount without losing this user's read state.
export function useNotices() {
  const readKey = `portal-notice-read-${sessionStore.user?.id}`
  const readIdsKey = `portal-notice-read-ids-${sessionStore.user?.id}`
  const readAt = ref(readStoredAt())
  const readIds = ref(readStoredIds())
  const latestAt = ref(siteStore.status?.notice_latest_at || 0)
  let timer

  function noticeAt(notice) {
    return Math.max(notice.created_at || 0, notice.updated_at || 0)
  }

  function isRead(notice) {
    const at = noticeAt(notice)
    return at <= readAt.value || (readIds.value.get(notice.id) || 0) >= at
  }

  const unreadCount = computed(() => notices.items.filter((n) => !isRead(n)).length)

  const notices = reactive({
    items: [],
    loading: false,
    saving: false,
    unreadCount,
    unread: computed(() => (notices.items.length ? unreadCount.value > 0 : latestAt.value > readAt.value)),
    isRead,
    load,
    markRead,
    markAllRead,
    create,
    update,
    remove,
  })

  // Site settings are cached for the session. Check independently so users already
  // on the page receive new notices without reloading or opening the dialog.
  async function checkLatest() {
    if (document.hidden) return
    try {
      latestAt.value = (await settingsApi.getStatus()).notice_latest_at || 0
    } catch {
      // A background failure keeps the current badge; retry on the next check.
    }
  }

  onMounted(() => {
    timer = setInterval(checkLatest, 30000)
    document.addEventListener('visibilitychange', checkLatest)
  })
  onUnmounted(() => {
    clearInterval(timer)
    document.removeEventListener('visibilitychange', checkLatest)
  })

  async function load() {
    notices.loading = true
    try {
      notices.items = (await noticesApi.listNotices()).items
    } catch (e) {
      toast.error(e.message)
    } finally {
      notices.loading = false
    }
  }

  function markRead(notice) {
    if (!notice || isRead(notice)) return
    readIds.value = new Map(readIds.value).set(notice.id, noticeAt(notice))
    if (notices.items.length && !unreadCount.value) {
      markAllRead()
      return
    }
    try {
      localStorage.setItem(readIdsKey, JSON.stringify([...readIds.value]))
    } catch {
      /* Storage may be unavailable; keep the in-memory read state. */
    }
  }

  function markAllRead() {
    const maxItemAt = notices.items.reduce((max, n) => Math.max(max, noticeAt(n)), 0)
    const at = Math.max(latestAt.value, maxItemAt)
    if (at > readAt.value) {
      readAt.value = at
      try {
        localStorage.setItem(readKey, String(at))
      } catch {
        /* Storage may be unavailable; keep the in-memory read state. */
      }
    }
    if (readIds.value.size) {
      readIds.value = new Map()
      try {
        localStorage.removeItem(readIdsKey)
      } catch {
        /* Storage may be unavailable; keep the in-memory read state. */
      }
    }
  }

  async function create(content) {
    if (notices.saving) return null
    notices.saving = true
    try {
      const { notice } = await noticesApi.adminCreateNotice({ content })
      notices.items = [notice, ...notices.items]
      markRead(notice)
      toast.success('通知已发布')
      return notice
    } catch (e) {
      toast.error(e.message)
      return null
    } finally {
      notices.saving = false
    }
  }

  async function update(id, content) {
    if (notices.saving) return null
    notices.saving = true
    try {
      const { notice } = await noticesApi.adminUpdateNotice(id, { content })
      notices.items = notices.items.map((item) => (item.id === notice.id ? notice : item))
      toast.success('通知已更新')
      return notice
    } catch (e) {
      toast.error(e.message)
      return null
    } finally {
      notices.saving = false
    }
  }

  async function remove(id) {
    if (notices.saving) return false
    notices.saving = true
    try {
      await noticesApi.adminDeleteNotice(id)
      notices.items = notices.items.filter((item) => item.id !== id)
      toast.success('通知已删除')
      return true
    } catch (e) {
      toast.error(e.message)
      return false
    } finally {
      notices.saving = false
    }
  }

  function readStoredAt() {
    try {
      return Number(localStorage.getItem(readKey)) || 0
    } catch {
      return 0
    }
  }

  function readStoredIds() {
    try {
      const parsed = JSON.parse(localStorage.getItem(readIdsKey) || '[]')
      return new Map(Array.isArray(parsed) ? parsed.filter(Array.isArray) : [])
    } catch {
      return new Map()
    }
  }

  return notices
}
