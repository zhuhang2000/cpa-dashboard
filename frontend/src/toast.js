import { reactive } from 'vue'

export const toasts = reactive([])
let seq = 0

function push(type, message, timeout = 2800) {
  const id = ++seq
  toasts.push({ id, type, message })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, timeout)
}

export const toast = {
  success: (m) => push('success', m),
  error: (m) => push('error', m, 4200),
  info: (m) => push('info', m),
}
