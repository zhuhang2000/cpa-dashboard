<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人设置</h1>
        <p class="page-desc">管理账号资料与登录密码。</p>
      </div>
    </div>

    <div class="grid grid-2" style="align-items: start">
      <div class="card">
        <div class="card-header"><div class="card-title">账号资料</div></div>
        <div class="card-body">
          <dl class="kv" style="margin: 0 0 20px">
            <dt>用户名</dt>
            <dd>{{ store.user?.username }}</dd>
            <dt>账号类型</dt>
            <dd>
              <StatusBadge class="plain" :map="ROLES" :value="store.user?.role" />
            </dd>
            <dt>注册时间</dt>
            <dd>{{ dateTime(store.user?.created_at) }}</dd>
            <dt>账户余额</dt>
            <dd class="num">{{ money(store.user?.balance || 0) }}</dd>
          </dl>
          <form @submit.prevent="saveProfile">
            <div class="field">
              <label for="email">邮箱</label>
              <input id="email" v-model.trim="email" class="input" type="email" placeholder="用于登录，可留空" />
            </div>
            <button class="btn btn-primary" :disabled="savingProfile || email === (store.user?.email || '')">
              保存资料
            </button>
          </form>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><div class="card-title">修改密码</div></div>
        <form class="card-body" @submit.prevent="changePassword">
          <div class="field">
            <label for="old-pass">当前密码</label>
            <input id="old-pass" v-model="pw.old" class="input" type="password" autocomplete="current-password" />
          </div>
          <div class="field">
            <label for="new-pass">新密码</label>
            <input
              id="new-pass"
              v-model="pw.next"
              class="input"
              type="password"
              autocomplete="new-password"
              placeholder="至少 8 位"
            />
          </div>
          <div class="field">
            <label for="new-pass2">确认新密码</label>
            <input id="new-pass2" v-model="pw.confirm" class="input" type="password" autocomplete="new-password" />
          </div>
          <div class="row-between wrap">
            <span class="muted" style="font-size: 12.5px">修改后其他设备上的登录会失效</span>
            <button class="btn btn-primary" :disabled="savingPassword">修改密码</button>
          </div>
        </form>
      </div>
    </div>

    <div class="card card-body row-between wrap">
      <div>
        <div class="card-title">退出登录</div>
        <div class="card-sub">在公共设备上使用后请记得退出。</div>
      </div>
      <button class="btn" @click="doLogout"><Icon name="logout" :size="16" />退出登录</button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '@/components/base/Icon.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { accountsApi } from '@/api/accounts'
import { ROLES } from '@/constants'
import { logout, setUser, store } from '@/store'
import { dateTime, money } from '@/utils/format'
import { toast } from '@/toast'

const router = useRouter()
const email = ref(store.user?.email || '')
const savingProfile = ref(false)
const savingPassword = ref(false)
const pw = reactive({ old: '', next: '', confirm: '' })

async function saveProfile() {
  savingProfile.value = true
  try {
    const data = await accountsApi.updateProfile({ email: email.value })
    setUser(data.user)
    toast.success('资料已保存')
  } catch (e) {
    toast.error(e.message)
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  if (pw.next.length < 8) return toast.error('新密码至少 8 位')
  if (pw.next !== pw.confirm) return toast.error('两次输入的新密码不一致')
  savingPassword.value = true
  try {
    await accountsApi.changePassword({ old_password: pw.old, new_password: pw.next })
    Object.assign(pw, { old: '', next: '', confirm: '' })
    toast.success('密码已修改')
  } catch (e) {
    toast.error(e.message)
  } finally {
    savingPassword.value = false
  }
}

async function doLogout() {
  await logout()
  router.replace('/login')
}
</script>
