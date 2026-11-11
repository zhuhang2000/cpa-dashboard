<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">运营概况</h1>
        <p class="page-desc">充值、消费与同步状态一览。</p>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="syncing" @click="sync">
          <Icon :name="syncing ? 'loader' : 'refresh'" :size="16" />立即同步
        </button>
      </div>
    </div>

    <template v-if="data">
      <template v-for="node in data.nodes" :key="node.id">
        <div v-if="node.cpamp.ok === false" class="alert alert-danger">
          <Icon name="alert" :size="16" />
          <div class="alert-body">
            <b>{{ node.id }} 用量同步失败：</b>{{ node.cpamp.error }}（数据库：<code>{{ node.usage_db }}</code
            >）
          </div>
        </div>
        <div v-if="!node.cpa_configured" class="alert alert-warning">
          <Icon name="alert" :size="16" />
          <div class="alert-body">
            {{ node.id }} 未配置 CPA 管理密钥：用户创建的密钥不会写入该节点，余额不足时也无法自动停用。请在
            <code>backend/core/.env</code> 中填写。
          </div>
        </div>
        <div v-else-if="node.cpa.ok === false" class="alert alert-danger">
          <Icon name="alert" :size="16" />
          <div class="alert-body">
            <b>{{ node.id }} 密钥同步失败：</b>{{ node.cpa.error }}
          </div>
        </div>
      </template>
      <div v-if="data.unpriced_models.length" class="alert alert-warning">
        <Icon name="tag" :size="16" />
        <div class="alert-body">
          近 24 小时有未定价模型被调用（未扣费）：
          <span v-for="(m, i) in data.unpriced_models" :key="m.model"
            ><code>{{ m.model }}</code
            >×{{ m.calls }}<template v-if="i < data.unpriced_models.length - 1">、</template></span
          >
          。<RouterLink to="/admin/prices">去设置价格</RouterLink>
        </div>
      </div>
    </template>

    <div class="grid grid-4">
      <StatCard
        label="用户总数"
        icon="users"
        :loading="!data"
        :value="num(data?.users.total || 0)"
        :sub="`今日新增 ${num(data?.users.today || 0)} · 活跃密钥 ${num(data?.keys_active || 0)}`"
      />
      <StatCard
        label="今日消费"
        icon="zap"
        tone="amber"
        :loading="!data"
        :value="money(data?.usage.today.cost || 0)"
        :sub="`${num(data?.usage.today.requests || 0)} 次请求 · 本月 ${money(data?.usage.month.cost || 0)}`"
      />
      <StatCard
        label="今日充值"
        icon="wallet"
        tone="green"
        :loading="!data"
        :value="money(data?.recharge.today || 0)"
        :sub="`本月 ${money(data?.recharge.month || 0)}`"
      >
        <template #action>
          <button type="button" class="btn btn-sm" @click="showRecords = true">充值记录</button>
        </template>
      </StatCard>
      <StatCard
        label="用户余额总计"
        icon="coins"
        tone="blue"
        :loading="!data"
        :value="money(data?.balance_total || 0)"
        sub="所有用户当前余额之和"
      />
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">近 14 天收支</div>
          <div class="card-sub">消费为按售价计算的扣费金额</div>
        </div>
        <div class="row legend">
          <span><i style="background: var(--chart-1)" />消费</span>
          <span><i style="background: var(--chart-2)" />充值</span>
        </div>
      </div>
      <div class="card-body">
        <div v-if="!data" class="skeleton" style="height: 240px" />
        <BarChart
          v-else
          :data="data.daily"
          :series="series"
          :format="money"
          :axis-format="(v) => `${currency()}${Number(v.toFixed(2)).toLocaleString('zh-CN')}`"
          :label-format="dayLabel"
          :height="240"
        />
      </div>
    </div>

    <div class="grid grid-2" style="align-items: start">
      <div class="card">
        <div class="card-header"><div class="card-title">本月消费 Top 用户</div></div>
        <EmptyState v-if="data && !data.top_users.length" icon="users" title="本月暂无消费" />
        <div v-else class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>用户</th>
                <th class="right">请求数</th>
                <th class="right">消费</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in data?.top_users || []" :key="u.id">
                <td class="cell-main">{{ u.username }}</td>
                <td class="right num">{{ num(u.requests) }}</td>
                <td class="right num">
                  <b>{{ money(u.cost) }}</b>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><div class="card-title">同步状态</div></div>
        <div v-if="data" class="card-body">
          <template v-for="(node, index) in data.nodes" :key="node.id">
            <div v-if="index" class="divider" />
            <div class="sync-block">
              <div class="row-between">
                <b><Icon name="box" :size="15" /> {{ node.id }}</b>
                <span class="row">
                  <span class="badge" :class="badge(node.cpamp.ok)">用量 {{ label(node.cpamp.ok) }}</span>
                  <span class="badge" :class="node.cpa_configured ? badge(node.cpa.ok) : ''">
                    密钥 {{ node.cpa_configured ? label(node.cpa.ok) : '未配置' }}
                  </span>
                </span>
              </div>
              <dl class="kv">
                <dt>CPA 地址</dt>
                <dd class="mono" style="font-size: 12px">{{ node.cpa_base_url || '—' }}</dd>
                <dt>用量库</dt>
                <dd class="mono" style="font-size: 12px">{{ node.usage_db }}</dd>
                <dt>最新事件</dt>
                <dd>{{ dateTime(node.cpamp.last_event_at, { seconds: true }) }}</dd>
                <dt>已计费请求</dt>
                <dd class="num">{{ num(node.cpamp.billed_events) }}（本次运行）</dd>
                <dt>读取游标</dt>
                <dd class="num">{{ node.cpamp.cursor ?? '—' }}</dd>
                <dt>上次密钥同步</dt>
                <dd>{{ dateTime(node.cpa.last_sync_at, { seconds: true }) }}</dd>
                <dt>可用密钥</dt>
                <dd class="num">{{ num(node.cpa.active_keys) }}</dd>
                <dt>密钥增 / 删</dt>
                <dd class="num">+{{ node.cpa.added }} / -{{ node.cpa.removed }}（本次运行）</dd>
              </dl>
            </div>
          </template>
        </div>
      </div>
    </div>

    <RechargeRecordsModal v-if="showRecords" @close="showRecords = false" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import BarChart from '@/components/base/BarChart.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import StatCard from '@/components/base/StatCard.vue'
import RechargeRecordsModal from '@/components/admin/overview/RechargeRecordsModal.vue'
import { settingsApi } from '@/api/settings'
import { usageApi } from '@/api/usage'
import { currency, dateTime, dayLabel, money, num } from '@/utils/format'
import { toast } from '@/toast'

const data = ref(null)
const syncing = ref(false)
const showRecords = ref(false)
const series = [
  { key: 'cost', label: '消费', color: 'var(--chart-1)' },
  { key: 'recharge', label: '充值', color: 'var(--chart-2)' },
]

function badge(ok) {
  return ok === true ? 'badge-success' : ok === false ? 'badge-danger' : ''
}
function label(ok) {
  return ok === true ? '正常' : ok === false ? '异常' : '等待中'
}

async function load() {
  try {
    data.value = await usageApi.adminOverview()
  } catch (e) {
    toast.error(e.message)
  }
}

async function sync() {
  syncing.value = true
  try {
    await settingsApi.adminRunSync()
    await load()
    toast.success('同步完成')
  } catch (e) {
    toast.error(e.message)
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.legend {
  gap: 16px;
  font-size: 12.5px;
  color: var(--muted);
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}
.sync-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sync-block b {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
