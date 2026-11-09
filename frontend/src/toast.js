import { reactive } from 'vue'

export const toasts = reactive([])
let seq = 0

// 返回的 Promise 在提示开始离场时 resolve，调用方可据此同步自身状态（如 CopyButton 的对勾）
function push(type, message, timeout) {
  const id = ++seq
  toasts.push({ id, type, message })
  return new Promise((resolve) =>
    setTimeout(() => {
      const i = toasts.findIndex((t) => t.id === id)
      if (i >= 0) toasts.splice(i, 1)
      resolve()
    }, timeout),
  )
}

export const toast = {
  success: (m) => push('success', m, 1000),
  error: (m) => push('error', m, 2000),
  info: (m) => push('info', m, 1000),
}
