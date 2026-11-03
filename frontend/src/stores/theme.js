import { reactive } from 'vue'

export const themeStore = reactive({
  theme: readTheme(),
})

function readTheme() {
  try {
    return localStorage.getItem('portal-theme') === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

export function toggleTheme() {
  const next = themeStore.theme === 'dark' ? 'light' : 'dark'
  themeStore.theme = next
  document.documentElement.setAttribute('data-theme', next)
  try {
    localStorage.setItem('portal-theme', next)
  } catch {
    /* ignore */
  }
}
