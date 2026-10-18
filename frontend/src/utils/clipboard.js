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
    let ok
    try {
      ok = document.execCommand('copy')
    } catch {
      ok = false
    }
    document.body.removeChild(ta)
    return ok
  }
}
