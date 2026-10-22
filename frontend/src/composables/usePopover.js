import { reactive, watch } from 'vue'

// Open state for a popup opened by clicking a trigger button. While it is open, pressing outside the
// trigger and `panel` or hitting Escape closes it, and Escape returns focus to the trigger. A popup
// placed from the trigger's position (`place(rect)` returns its style) also closes on scroll or
// resize, which would leave it floating in the wrong spot.
export function usePopover({ panel, place } = {}) {
  const popover = reactive({ open: false, style: {}, toggle, close })
  let trigger = null

  // The trigger's click handler; clicking another trigger moves the popup to that one.
  function toggle(event) {
    if (popover.open && event.currentTarget === trigger) return close()
    trigger = event.currentTarget
    if (place) popover.style = place(trigger.getBoundingClientRect())
    popover.open = true
  }

  function close({ focus = false } = {}) {
    if (!popover.open) return
    popover.open = false
    if (focus) trigger?.focus()
  }

  function onPointerDown(e) {
    if (!trigger?.contains(e.target) && !panel?.value?.contains(e.target)) close()
  }
  function onKeydown(e) {
    if (e.key !== 'Escape') return
    // Handled while capturing so an enclosing dialog does not close too.
    e.preventDefault()
    e.stopImmediatePropagation()
    close({ focus: true })
  }
  function onScroll(e) {
    if (!panel?.value?.contains(e.target)) close()
  }
  function onResize() {
    close()
  }

  // Only an open popup listens; closing it or unmounting its component removes the listeners.
  watch(
    () => popover.open,
    (open, _, onCleanup) => {
      if (!open) return
      document.addEventListener('pointerdown', onPointerDown)
      document.addEventListener('keydown', onKeydown, true)
      if (place) {
        document.addEventListener('scroll', onScroll, true)
        window.addEventListener('resize', onResize)
      }
      onCleanup(() => {
        document.removeEventListener('pointerdown', onPointerDown)
        document.removeEventListener('keydown', onKeydown, true)
        document.removeEventListener('scroll', onScroll, true)
        window.removeEventListener('resize', onResize)
      })
    },
  )

  return popover
}
