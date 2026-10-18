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

// Copy text that is still being fetched. Safari only allows clipboard writes inside the
// click handler, so it gets a ClipboardItem backed by the pending promise.
// Resolves to null when the promise produced nothing (the caller already reported why).
export async function copyLazy(promise) {
  if (window.ClipboardItem && navigator.clipboard?.write) {
    try {
      const blob = promise.then((text) => {
        if (!text) throw new Error('empty')
        return new Blob([text], { type: 'text/plain' })
      })
      await navigator.clipboard.write([new window.ClipboardItem({ 'text/plain': blob })])
      return true
    } catch {
      /* fall back below */
    }
  }
  const text = await promise
  return text ? copyText(text) : null
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    let ok = false
    try {
      ok = document.execCommand('copy')
    } catch {
      ok = false
    }
    document.body.removeChild(ta)
    return ok
  }
}
