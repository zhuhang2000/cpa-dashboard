import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { noticesApi } from '@/api/notices'
import { settingsApi } from '@/api/settings'
import { siteStore, sessionStore } from '@/stores'
import { toast } from '@/toast'

// One controller per bell. Dialogs can unmount without losing this user's read state.
export function useNotices() {
  const readKey = `portal-notice-read-${sessionStore.user?.id}`
  const readAt = ref(readStored())
  const latestAt = ref(siteStore.status?.notice_latest_at || 0)
  let timer
  const notices = reactive({
    items: [],
    loading: false,
    saving: false,
    // Snapshot from before opening, used to highlight newly received notices.
    seenBefore: 0,
    unread: computed(() => latestAt.value > readAt.value),
    load,
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
    notices.seenBefore = readAt.value
    notices.loading = true
    try {
      notices.items = (await noticesApi.listNotices()).items
      // Only mark notices actually returned by a successful request as read.
      markRead(notices.items[0]?.created_at)
    } catch (e) {
      toast.error(e.message)
    } finally {
      notices.loading = false
    }
  }

  async function create(content) {
    if (notices.saving) return null
    notices.saving = true
    try {
      const { notice } = await noticesApi.adminCreateNotice({ content })
      notices.items = [notice, ...notices.items]
      markRead(notice.created_at)
      // The publisher has seen it, so it is not tagged 未读 in the open dialog either.
      notices.seenBefore = notice.created_at
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

  function markRead(at) {
    if (!at || at <= readAt.value) return
    readAt.value = at
    try {
      localStorage.setItem(readKey, String(at))
    } catch {
      /* Storage may be unavailable; keep the in-memory read state. */
    }
  }
  function readStored() {
    try {
      return Number(localStorage.getItem(readKey)) || 0
    } catch {
      return 0
    }
  }

  return notices
}
