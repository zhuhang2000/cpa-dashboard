import { computed, reactive, ref, toValue } from 'vue'
import { store } from '@/store'

// "Close" for a banner that lasts until the next sign-in: every login bumps last_login_at, so the
// stored session stops matching and the banner shows again. A new `key` (say, for new content) also
// shows it again. `key` may be a string, ref or getter.
export function useDismissUntilNextLogin(key) {
  const session = computed(() => `${store.user?.id}:${store.user?.last_login_at}`)
  // Kept in memory too, so closing still works when storage is unavailable.
  const closed = ref({})
  const dismissed = computed(() => {
    const name = toValue(key)
    return (closed.value[name] ?? readStored(name)) === session.value
  })

  function dismiss() {
    const name = toValue(key)
    closed.value = { ...closed.value, [name]: session.value }
    try {
      localStorage.setItem(name, session.value)
    } catch {
      /* Storage may be unavailable; the in-memory copy still hides it. */
    }
  }

  return reactive({ dismissed, dismiss })
}

function readStored(name) {
  try {
    return localStorage.getItem(name)
  } catch {
    return null
  }
}
