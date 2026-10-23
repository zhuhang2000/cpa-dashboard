<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-desc">
          修改后立即生效，覆盖 config.json 中的同名配置。连接类配置（CPA 地址、管理密钥、支付参数）请在 config.json
          中修改。
        </p>
      </div>
    </div>

    <div v-if="!form" class="card card-body stack" style="gap: 12px">
      <div v-for="i in 5" :key="i" class="skeleton" style="height: 38px" />
    </div>
    <form v-else class="grid grid-2" style="align-items: start" @submit.prevent="save">
      <div class="card">
        <div class="card-header"><div class="card-title">站点</div></div>
        <div class="card-body">
          <div class="field">
            <label for="s-name">站点名称</label>
            <input id="s-name" v-model.trim="form.site_name" class="input" maxlength="40" />
          </div>
          <div class="field">
            <label for="s-base">API Base URL</label>
            <input
              id="s-base"
              v-model.trim="form.public_api_base"
              class="input mono"
              maxlength="200"
              placeholder="https://api.example.com"
            />
            <div class="field-hint">用户调用接口的地址（即 CLIProxyAPI 对外地址），显示在概览页的快速开始中</div>
          </div>
          <div class="field">
            <label for="s-ann">公告</label>
            <textarea
              id="s-ann"
              v-model="form.announcement"
              class="textarea"
              rows="4"
              maxlength="1000"
              placeholder="显示在用户概览页顶部，留空则不显示"
            />
          </div>
          <div class="field" style="margin-bottom: 0">
            <label class="toggle">
              <input v-model="form.allow_register" type="checkbox" />
              <span class="toggle-track" />
              开放注册
            </label>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><div class="card-title">计费</div></div>
        <div class="card-body">
          <div class="field">
            <label class="toggle">
              <input v-model="form.use_cpamp_prices" type="checkbox" />
              <span class="toggle-track" />
              未单独定价的模型使用官方价
            </label>
            <div class="field-hint">官方价来自 CPA Manager Plus 同步的模型价格（美元 / 百万 tokens）</div>
          </div>
          <div class="field">
            <label for="s-discount">官方价折扣</label>
            <div class="input-group">
              <input id="s-discount" v-model.number="discountInput" class="input" type="number" min="0" step="any" />
              <span class="input-suffix">折</span>
            </div>
            <div class="field-hint">10 为不打折，85 折填 8.5。只对官方价打折，自定义价格和默认价格不受影响</div>
          </div>
          <div class="grid grid-2" style="gap: 12px">
            <div class="field">
              <label for="s-din">默认输入价格</label>
              <input
                id="s-din"
                v-model.number="form.default_input_price"
                class="input"
                type="number"
                min="0"
                step="any"
              />
            </div>
            <div class="field">
              <label for="s-dout">默认输出价格</label>
              <input
                id="s-dout"
                v-model.number="form.default_output_price"
                class="input"
                type="number"
                min="0"
                step="any"
              />
            </div>
          </div>
          <div class="alert alert-warning">
            <Icon name="alert" :size="16" />
            <div class="alert-body">
              默认价格用于既没有自定义价格、也找不到官方价的模型（单位 {{ currency() }} / 百万 tokens）。两者都为 0
              时这类模型不扣费。
            </div>
          </div>
        </div>
        <div class="card-footer" style="justify-content: flex-end">
          <button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存设置' }}</button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import Icon from '@/components/base/Icon.vue'
import { settingsApi } from '@/api/settings'
import { refreshStatus } from '@/store'
import { currency } from '@/utils/format'
import { toast } from '@/toast'

const form = ref(null)
// Admins type 折 (8 = 8 折) while the API stores the billed share of the official price (0.8).
const discountInput = ref(10)
const saving = ref(false)

function fill(settings) {
  form.value = settings
  discountInput.value = Number((settings.cpamp_price_discount * 10).toFixed(2))
}

async function save() {
  saving.value = true
  try {
    const data = await settingsApi.adminPutSettings({ ...form.value, cpamp_price_discount: discountInput.value / 10 })
    fill(data.settings)
    await refreshStatus()
    toast.success('设置已保存')
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    fill((await settingsApi.adminGetSettings()).settings)
  } catch (e) {
    toast.error(e.message)
  }
})
</script>
