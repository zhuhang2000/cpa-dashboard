<template>
  <div class="stack">
    <div v-if="announcement && !announcementHidden" class="alert alert-info announcement">
      <Icon name="megaphone" :size="16" />
      <div class="alert-body" style="white-space: pre-line">{{ announcement }}</div>
      <button class="alert-close" aria-label="关闭公告" @click="hideAnnouncement"><Icon name="x" :size="16" /></button>
    </div>

    <div v-if="store.keyCount === 0" class="card onboarding">
      <div>
        <div class="card-title">开始使用</div>
        <p class="muted" style="margin-top: 4px">创建第一个 API 密钥，然后把它填进你的客户端即可开始调用。</p>
      </div>
      <RouterLink to="/keys?create=1" class="btn btn-primary"><Icon name="plus" :size="16" />创建 API 密钥</RouterLink>
    </div>

    <div class="grid grid-4">
      <StatCard
        label="账户余额"
        icon="wallet"
        :value="money(store.user?.balance || 0)"
        :value-class="(store.user?.balance ?? 1) <= 0 ? 'text-danger' : ''"
        :sub="balanceSub"
      >
        <template #action>
          <RouterLink to="/recharge" class="btn btn-sm btn-primary">充值</RouterLink>
        </template>
      </StatCard>
      <StatCard
        label="今日消费"
        icon="zap"
        tone="amber"
        :loading="!summary"
        :value="money(summary?.today.cost || 0)"
        :sub="`${num(summary?.today.requests || 0)} 次请求 · ${tokens(summary?.today.tokens || 0)} tokens`"
      />
      <StatCard
        label="本月消费"
        icon="receipt"
        tone="blue"
        :loading="!summary"
        :value="money(summary?.month.cost || 0)"
        :sub="`${num(summary?.month.requests || 0)} 次请求 · ${tokens(summary?.month.tokens || 0)} tokens`"
      />
      <StatCard
        label="累计调用"
        icon="activity"
        tone="green"
        :loading="!summary"
        :value="num(summary?.total.requests || 0)"
        :sub="`累计消费 ${money(summary?.total.cost || 0)}`"
      />
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">消费趋势</div>
          <div class="card-sub">
            近 {{ days }} 天 · {{ money(summary?.range.cost || 0) }} · {{ num(summary?.range.requests || 0) }} 次请求
          </div>
        </div>
        <div class="row wrap">
          <div class="tabs">
            <button
              v-for="m in metrics"
              :key="m.key"
              class="tab"
              :class="{ active: metric === m.key }"
              @click="metric = m.key"
            >
              {{ m.label }}
            </button>
          </div>
          <div class="tabs">
            <button v-for="d in [7, 30]" :key="d" class="tab" :class="{ active: days === d }" @click="setDays(d)">
              {{ d }} 天
            </button>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div v-if="!summary" class="skeleton" style="height: 240px" />
        <BarChart
          v-else
          :data="summary.daily"
          :series="chartSeries"
          :format="currentMetric.format"
          :axis-format="currentMetric.axis"
          :label-format="dayLabel"
          :integer="metric !== 'cost'"
          :height="250"
        />
      </div>
    </div>

    <div class="grid grid-main-side">
      <section class="card connection-card" aria-labelledby="connection-title">
        <div class="card-header">
          <div>
            <h2 id="connection-title" class="card-title">API 接入</h2>
          </div>
          <a
            href="https://help.tromino.wiki/guidance/codex"
            target="_blank"
            rel="noopener"
            class="btn btn-sm btn-ghost ext-link"
          >
            Codex 介绍<Icon name="external" :size="14" />
          </a>
        </div>
        <ol class="steps">
          <li class="step">
            <span class="step-num">1</span>
            <div class="step-label">接入地址<span>Base URL</span></div>
            <div class="step-value">
              <code v-if="baseUrl">{{ baseUrl }}</code>
              <span v-else class="muted">管理员尚未配置，请联系管理员</span>
            </div>
            <CopyButton v-if="baseUrl" class="step-action" :text="baseUrl" label="复制" />
          </li>
          <li class="step">
            <span class="step-num">2</span>
            <div class="step-label">API 密钥<span>API Key</span></div>
            <div class="step-value muted">
              {{ store.keyCount === 0 ? '还没有密钥，先创建一个' : `已有 ${store.keyCount} 个，在密钥页查看并复制` }}
            </div>
            <RouterLink
              :to="store.keyCount === 0 ? '/keys?create=1' : '/keys'"
              class="btn btn-sm step-action"
              :class="store.keyCount === 0 ? 'btn-primary' : 'btn-ghost'"
            >
              {{ store.keyCount === 0 ? '创建密钥' : '管理密钥' }}<Icon name="chevron-right" :size="14" />
            </RouterLink>
          </li>
          <li class="step">
            <span class="step-num">3</span>
            <div class="step-label">配置 Codex<span>Setup</span></div>
            <div class="step-value muted">推荐用 Cockpit Tools 填入以上两项</div>
            <a
              href="https://help.tromino.wiki/guidance/api-guide#tool-intro"
              target="_blank"
              rel="noopener"
              class="btn btn-sm btn-ghost step-action ext-link"
              title="集中管理接入地址与密钥"
            >
              Cockpit Tools<Icon name="external" :size="14" />
            </a>
          </li>
        </ol>
      </section>

      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">模型消费排行</div>
            <div class="card-sub">近 {{ days }} 天</div>
          </div>
          <RouterLink to="/usage" class="btn btn-sm btn-ghost"
            >查看明细<Icon name="chevron-right" :size="14"
          /></RouterLink>
        </div>
        <div class="card-body">
          <div v-if="!summary" class="stack" style="gap: 14px">
            <div v-for="i in 4" :key="i" class="skeleton" style="height: 34px" />
          </div>
          <EmptyState
            v-else-if="!summary.by_model.length"
            icon="chart"
            title="暂无调用记录"
            desc="使用 API 密钥调用后，这里会显示各模型的消费"
          />
          <div v-else class="rank">
            <div v-for="m in summary.by_model" :key="m.model" class="rank-item">
              <div class="row-between">
                <span class="truncate mono" :title="m.model">{{ m.model }}</span>
                <b class="num">{{ money(m.cost) }}</b>
              </div>
              <div class="progress"><div :style="{ width: `${share(m.cost)}%` }" /></div>
              <div class="cell-sub">{{ num(m.requests) }} 次 · {{ tokens(m.tokens) }} tokens</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import BarChart from '@/components/BarChart.vue'
import CopyButton from '@/components/CopyButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import Icon from '@/components/Icon.vue'
import StatCard from '@/components/StatCard.vue'
import { usageApi } from '@/api/usage'
import { refreshUser, store } from '@/store'
import { currency, dayLabel, money, num, tokens } from '@/utils/format'
import { toast } from '@/toast'

const summary = ref(null)
const days = ref(30)

const balanceSub = computed(() => {
  if ((store.user?.balance ?? 1) > 0) return `累计充值 ${money(store.user?.total_recharge || 0)}`
  return store.keyCount > 0 ? '余额不足，密钥已暂停调用' : '充值后即可开始调用'
})
const metric = ref('cost')

const metrics = [
  { key: 'cost', label: '费用', format: (v) => money(v), axis: (v) => `${currency()}${trimNum(v)}` },
  { key: 'requests', label: '请求数', format: (v) => `${num(v)} 次`, axis: (v) => trimNum(v) },
  { key: 'tokens', label: 'Tokens', format: (v) => tokens(v), axis: (v) => tokens(v) },
]
const currentMetric = computed(() => metrics.find((m) => m.key === metric.value))
const chartSeries = computed(() => [{ key: metric.value, label: currentMetric.value.label, color: 'var(--chart-1)' }])

function trimNum(v) {
  return Number(v.toFixed(v < 1 ? 3 : 2)).toLocaleString('zh-CN')
}
function share(cost) {
  const max = Math.max(...summary.value.by_model.map((m) => m.cost), 0)
  return max > 0 ? Math.max(2, (cost / max) * 100) : 0
}

const announcement = computed(() => (store.status?.announcement || '').trim())
const announcementKey = computed(() => `portal-ann-${hash(announcement.value)}`)
// Closing hides the announcement for the current sign-in only: every login bumps last_login_at, so the
// next one shows it again (as does a new announcement, which gets a new key).
const loginSession = computed(() => `${store.user?.id}:${store.user?.last_login_at}`)
const announcementHidden = ref(false)
function hash(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return h
}
function hideAnnouncement() {
  announcementHidden.value = true
  try {
    localStorage.setItem(announcementKey.value, loginSession.value)
  } catch {
    /* ignore */
  }
}

const baseUrl = computed(() => (store.status?.public_api_base || '').replace(/\/+$/, ''))

async function load() {
  try {
    summary.value = await usageApi.usageSummary({ days: days.value })
  } catch (e) {
    toast.error(e.message)
  }
}
function setDays(d) {
  if (days.value === d) return
  days.value = d
  summary.value = null
  load()
}

onMounted(() => {
  try {
    announcementHidden.value = localStorage.getItem(announcementKey.value) === loginSession.value
  } catch {
    /* ignore */
  }
  refreshUser()
  load()
})
</script>

<style scoped>
.connection-card {
  align-self: start;
}
.steps {
  margin: 0;
  padding: 4px 20px;
  list-style: none;
}
/* Number · label · value · action on one line, so returning users can scan it at a glance. */
.step {
  display: grid;
  grid-template-columns: 22px 92px minmax(0, 1fr) auto;
  grid-template-areas: 'num label value action';
  align-items: center;
  column-gap: 12px;
  min-height: 60px;
  padding: 10px 0;
}
.step + .step {
  border-top: 1px solid var(--border);
}
.step-num {
  grid-area: num;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 12px;
  font-weight: 600;
}
.step-label {
  grid-area: label;
  color: var(--text-2);
  font-size: 13px;
  font-weight: 500;
}
.step-label > span {
  display: block;
  margin-top: 1px;
  color: var(--faint);
  font-size: 11px;
  font-weight: 400;
}
.step-value {
  grid-area: value;
  min-width: 0;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.step-value code {
  color: var(--text);
}
.step-action {
  grid-area: action;
}
/* External resources get a tinted fill to set them apart from the in-page actions. */
.ext-link {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.ext-link:hover {
  background: color-mix(in srgb, var(--accent) 18%, var(--surface));
}
@media (max-width: 540px) {
  .steps {
    padding: 4px 16px;
  }
  .step {
    grid-template-columns: 22px minmax(0, 1fr) auto;
    grid-template-areas:
      'num label action'
      '. value value';
    row-gap: 4px;
  }
  .step-label > span {
    display: inline;
    margin-left: 6px;
  }
}

/* As wide as its text rather than the full row. */
.announcement {
  align-self: flex-start;
}
.onboarding {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  flex-wrap: wrap;
  background: linear-gradient(120deg, var(--accent-soft), var(--surface) 70%);
}
.rank {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.rank-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
