<template>
  <AuthShell>
    <h1 class="auth-title">欢迎回来</h1>
    <p class="auth-sub">登录你的账号</p>
    <form novalidate @submit.prevent="submit">
      <div class="field">
        <label for="login-user">账号</label>
        <input
          id="login-user"
          v-model.trim="form.username"
          class="input"
          autocomplete="username"
          placeholder="用户名或邮箱"
          autofocus
        />
      </div>
      <div class="field">
        <label for="login-pass">密码</label>
        <PasswordInput id="login-pass" v-model="form.password" autocomplete="current-password" />
      </div>
      <div v-if="error" class="alert alert-danger" style="margin-bottom: 16px">
        <Icon name="alert" :size="16" />
        <div class="alert-body">{{ error }}</div>
      </div>
      <button class="btn btn-primary btn-lg btn-block" :disabled="loading">
        <Icon v-if="loading" name="loader" :size="16" />
        {{ loading ? '登录中…' : '登录' }}
      </button>
    </form>
    <p class="auth-foot">
      <template v-if="store.status?.allow_register">
        还没有账号？<RouterLink to="/register">立即注册</RouterLink>
      </template>
      <template v-else>暂未开放注册，请联系管理员</template>
    </p>
  </AuthShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthShell from '@/layouts/AuthShell.vue'
import Icon from '@/components/base/Icon.vue'
import PasswordInput from '@/components/base/PasswordInput.vue'
import { accountsApi } from '@/api/accounts'
import { setUser, store } from '@/store'

const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (!form.username || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const data = await accountsApi.login(form)
    setUser(data.user)
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>
