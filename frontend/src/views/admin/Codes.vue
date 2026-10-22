<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">兑换码</h1>
        <p class="page-desc">批量生成充值或赠送兑换码，用户兑换后余额立即到账。赠送不计入充值统计。</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" @click="genOpen = true"><Icon name="plus" :size="16" />生成兑换码</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="row wrap">
          <div class="tabs">
            <button
              v-for="s in statuses"
              :key="s.key"
              class="tab"
              :class="{ active: status === s.key }"
              @click="setStatus(s.key)"
            >
              {{ s.label }}
            </button>
          </div>
          <select
            v-model="batch"
            class="select input-sm"
            style="width: auto; min-width: 140px"
            aria-label="批次"
            @change="codes.load(1)"
          >
            <option value="">全部批次</option>
            <option v-for="b in codes.batches" :key="b" :value="b">{{ b }}</option>
          </select>
          <form class="input-group has-prefix search" @submit.prevent="codes.load(1)">
            <span class="input-prefix"><Icon name="search" :size="15" /></span>
            <input v-model.trim="q" class="input input-sm" placeholder="搜索兑换码" aria-label="搜索兑换码" />
          </form>
        </div>
      </div>
      <div v-if="codes.loading && !codes.items.length" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState v-else-if="!codes.items.length" icon="ticket" title="暂无兑换码" desc="点击右上角“生成兑换码”创建" />
      <div v-else class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>兑换码</th>
              <th class="right">面额</th>
              <th>类型</th>
              <th>批次</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>使用者</th>
              <th class="actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in codes.items" :key="c.code">
              <td>
                <div class="row" style="gap: 4px">
                  <code class="nowrap">{{ c.code }}</code>
                  <CopyButton :text="c.code" />
                </div>
              </td>
              <td class="right num">
                <b>{{ money(c.amount) }}</b>
              </td>
              <td><StatusBadge :map="REDEEM_TYPES" :value="c.type" /></td>
              <td>{{ c.batch || '—' }}</td>
              <td>
                <StatusBadge :map="REDEEM_STATES" :value="codeState(c)" />
              </td>
              <td class="nowrap">
                {{ dateTime(c.created_at) }}
                <div v-if="c.expires_at" class="cell-sub">有效期至 {{ date(c.expires_at) }}</div>
              </td>
              <td class="nowrap">
                <template v-if="c.used_by">
                  {{ c.used_by }}
                  <div class="cell-sub">{{ dateTime(c.used_at) }}</div>
                </template>
                <span v-else class="faint">—</span>
              </td>
              <td class="actions">
                <button
                  v-if="c.status === RedeemStatus.UNUSED || c.status === RedeemStatus.DISABLED"
                  class="link-btn danger"
                  :disabled="!!deletingCode"
                  @click="remove(c)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="codes.total" class="card-footer">
        <Pagination :page="codes.page" :total="codes.total" :page-size="codes.page_size" @change="codes.load" />
      </div>
    </div>

    <Modal :open="genOpen" title="生成兑换码" @close="genOpen = false">
      <form id="gen-form" @submit.prevent="generate">
        <div class="grid grid-2" style="gap: 12px">
          <div class="field">
            <label for="gen-amount">面额</label>
            <div class="input-group has-prefix">
              <span class="input-prefix">{{ currency() }}</span>
              <input id="gen-amount" v-model="gen.amount" class="input" type="number" min="0.01" step="0.01" required />
            </div>
          </div>
          <div class="field">
            <label for="gen-count">数量</label>
            <input id="gen-count" v-model="gen.count" class="input" type="number" min="1" max="500" required />
          </div>
        </div>
        <div class="field">
          <label for="gen-type">类型</label>
          <select id="gen-type" v-model="gen.type" class="select">
            <option v-for="(entry, value) in REDEEM_TYPES" :key="value" :value="value">{{ entry.label }}</option>
          </select>
          <div class="field-hint">
            {{ gen.type === RedeemType.GIFT ? '赠送仅增加余额，不计入充值统计。' : '充值增加余额，并计入充值统计。' }}
          </div>
        </div>
        <div class="field">
          <label for="gen-batch">批次名称 <span class="faint">（选填）</span></label>
          <input
            id="gen-batch"
            v-model.trim="gen.batch"
            class="input"
            maxlength="32"
            placeholder="例如：2026-10 发卡平台"
          />
        </div>
        <div class="field">
          <label for="gen-exp">有效期（天） <span class="faint">（选填）</span></label>
          <input
            id="gen-exp"
            v-model="gen.expires_days"
            class="input"
            type="number"
            min="1"
            max="3650"
            placeholder="不填表示永久有效"
          />
        </div>
      </form>
      <template #footer>
        <button class="btn" @click="genOpen = false">取消</button>
        <button class="btn btn-primary" form="gen-form" :disabled="saving">生成</button>
      </template>
    </Modal>

    <Modal :open="!!generated" title="兑换码已生成" wide @close="generated = null">
      <p class="muted" style="margin-bottom: 10px">
        类型：{{ REDEEM_TYPES[generated?.type]?.label }}，共 {{ generated?.codes.length }} 个，面额
        {{ money(generated?.amount || 0) }}{{ generated?.batch ? `，批次「${generated.batch}」` : '' }}。
      </p>
      <textarea class="textarea mono" readonly rows="10" :value="generated?.codes.join('\n')" style="font-size: 13px" />
      <template #footer>
        <button class="btn" @click="download"><Icon name="download" :size="16" />下载 TXT</button>
        <CopyButton :text="generated?.codes.join('\n') || ''" label="复制全部" variant="default" size="md" />
        <button class="btn btn-primary" @click="generated = null">完成</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import CopyButton from '@/components/base/CopyButton.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Modal from '@/components/base/Modal.vue'
import Pagination from '@/components/base/Pagination.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { billingApi } from '@/api/billing'
import { usePagedList } from '@/composables/usePagedList'
import { REDEEM_STATES, REDEEM_TYPES, RedeemState, RedeemStatus, RedeemType } from '@/constants'
import { currency, date, dateTime, money } from '@/utils/format'
import { toast } from '@/toast'

const statuses = [
  { key: '', label: '全部' },
  ...Object.values(RedeemStatus).map((key) => ({ key, label: REDEEM_STATES[key].label })),
]
const status = ref('')
const batch = ref('')
const q = ref('')
const codes = usePagedList(
  billingApi.adminListCodes,
  () => ({ status: status.value, batch: batch.value, q: q.value }),
  { batches: [] },
)
const saving = ref(false)
const deletingCode = ref(null)
const genOpen = ref(false)
const generated = ref(null)
const gen = reactive({ amount: 50, count: 10, type: RedeemType.RECHARGE, batch: '', expires_days: '' })

function codeState(c) {
  const expired = c.status === RedeemStatus.UNUSED && c.expires_at && c.expires_at <= Date.now()
  return expired ? RedeemState.EXPIRED : c.status
}
function setStatus(s) {
  status.value = s
  codes.load(1)
}

async function generate() {
  saving.value = true
  try {
    generated.value = await billingApi.adminCreateCodes({
      amount: gen.amount,
      count: Number(gen.count),
      type: gen.type,
      batch: gen.batch,
      expires_days: gen.expires_days ? Number(gen.expires_days) : null,
    })
    genOpen.value = false
    await codes.load(1)
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(c) {
  if (deletingCode.value) return
  deletingCode.value = c.code
  try {
    await billingApi.adminDeleteCode(c.code)
    toast.success('已删除兑换码')
    const lastPage = Math.max(1, Math.ceil((codes.total - 1) / codes.page_size))
    await codes.load(Math.min(codes.page, lastPage))
  } catch (e) {
    toast.error(e.message)
  } finally {
    deletingCode.value = null
  }
}

function download() {
  const blob = new Blob([generated.value.codes.join('\n') + '\n'], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `redeem-codes-${generated.value.type}-${generated.value.batch || 'batch'}-${Date.now()}.txt`
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

onMounted(() => codes.load(1))
</script>

<style scoped>
.search {
  width: 220px;
  max-width: 100%;
}
.search .input {
  padding-left: 32px;
}
</style>
