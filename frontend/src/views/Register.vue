<template>
  <AuthShell>
    <h1 class="auth-title">创建账号</h1>
    <p class="auth-sub">注册后按新手指引接入Codex</p>

    <div v-if="!store.status?.allow_register" class="alert alert-warning">
      <Icon name="lock" :size="16" />
      <div class="alert-body">当前未开放注册，请联系管理员开通账号。</div>
    </div>

    <form v-else novalidate @submit.prevent="submit">
      <div class="field">
        <label for="reg-user">用户名</label>
        <input
          id="reg-user"
          v-model.trim="form.username"
          class="input"
          autocomplete="username"
          placeholder="3-32 位字母、数字、下划线"
          autofocus
        />
      </div>
      <div class="field">
        <label for="reg-email">邮箱 <span class="faint">（选填）</span></label>
        <input
          id="reg-email"
          v-model.trim="form.email"
          class="input"
          type="email"
          autocomplete="email"
          placeholder="name@example.com"
        />
      </div>
      <div class="field">
        <label for="reg-pass">密码</label>
        <PasswordInput
          id="reg-pass"
          v-model="form.password"
          v-model:visible="showPassword"
          autocomplete="new-password"
          placeholder="至少 8 位"
        />
        <div class="strength">
          <span v-for="i in 4" :key="i" :class="{ on: strength >= i }" :data-level="strength" />
        </div>
      </div>
      <div class="field">
        <label for="reg-pass2">确认密码</label>
        <input
          id="reg-pass2"
          v-model="form.confirm"
          class="input"
          :type="showPassword ? 'text' : 'password'"
          autocomplete="new-password"
          placeholder="再次输入密码"
        />
      </div>
      <div v-if="error" class="alert alert-danger" style="margin-bottom: 16px">
        <Icon name="alert" :size="16" />
        <div class="alert-body">{{ error }}</div>
      </div>
      <button class="btn btn-primary btn-lg btn-block" :disabled="loading">
        <Icon v-if="loading" name="loader" :size="16" />
        {{ loading ? '注册中…' : '注册并登录' }}
      </button>
    </form>
    <p class="auth-foot">已有账号？<RouterLink to="/login">直接登录</RouterLink></p>
  </AuthShell>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthShell from '@/layouts/AuthShell.vue'
import Icon from '@/components/base/Icon.vue'
import PasswordInput from '@/components/base/PasswordInput.vue'
import { accountsApi } from '@/api/accounts'
import { setUser, store } from '@/store'
import { toast } from '@/toast'

const router = useRouter()
const form = reactive({ username: '', email: '', password: '', confirm: '' })
const loading = ref(false)
const error = ref('')
// The confirmation field shows and hides together with the password.
const showPassword = ref(false)

const strength = computed(() => {
  const p = form.password
  if (!p) return 0
  let score = p.length >= 8 ? 1 : 0
  if (p.length >= 12) score++
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score++
  if (/\d/.test(p) && /[^A-Za-z0-9]/.test(p)) score++
  return Math.max(1, score)
})

async function submit() {
  error.value = ''
  if (!/^[A-Za-z0-9_-]{3,32}$/.test(form.username)) {
    error.value = '用户名需为 3-32 位字母、数字、下划线或短横线'
    return
  }
  if (form.password.length < 8) {
    error.value = '密码至少 8 位'
    return
  }
  if (form.password !== form.confirm) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const data = await accountsApi.register({
      username: form.username,
      email: form.email,
      password: form.password,
    })
    setUser(data.user)
    toast.success('注册成功，欢迎加入！')
    router.replace('/keys')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.strength {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  margin-top: 2px;
}
.strength span {
  height: 4px;
  border-radius: 2px;
  background: var(--chart-track);
}
.strength span.on[data-level='1'] {
  background: var(--danger);
}
.strength span.on[data-level='2'] {
  background: var(--warning);
}
.strength span.on[data-level='3'],
.strength span.on[data-level='4'] {
  background: var(--success);
}
</style>
