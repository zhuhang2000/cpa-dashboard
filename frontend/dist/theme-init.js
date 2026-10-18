// Applies the saved theme before first paint (kept external to satisfy the CSP).
try {
  var t = localStorage.getItem('portal-theme')
  if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t)
} catch (e) {}
