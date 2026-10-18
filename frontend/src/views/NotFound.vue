<template>
  <div class="notfound">
    <div class="code-404">404</div>
    <h1>页面不存在</h1>
    <p class="muted">你访问的页面可能已被移除，或链接有误。</p>
    <RouterLink to="/" class="btn btn-primary">返回首页</RouterLink>
  </div>
</template>

<style scoped>
.notfound {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
}
.code-404 {
  font-size: 72px;
  font-weight: 800;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, var(--accent), #8b5cf6);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1;
}
h1 {
  font-size: 20px;
}
</style>
