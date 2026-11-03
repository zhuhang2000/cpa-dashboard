// Applies the saved theme before first paint (kept external to satisfy the CSP).
var theme = 'light'
try {
  if (localStorage.getItem('portal-theme') === 'dark') theme = 'dark'
} catch (e) {}
document.documentElement.setAttribute('data-theme', theme)
