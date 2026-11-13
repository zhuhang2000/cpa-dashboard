<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">运营概况</h1>
        <p class="page-desc">充值与消费一览。节点同步状态和分流设置在「节点分流」页面。</p>
      </div>
    </div>

    <template v-if="data">
      <div v-if="data.sync_issues.length" class="alert alert-danger">
        <Icon name="alert" :size="16" />
        <div class="alert-body">
          {{ data.sync_issues.join('、') }} 的用量或密钥同步异常。
          <RouterLink to="/admin/routing">查看详情</RouterLink>
        </div>
      </div>
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
import { usageApi } from '@/api/usage'
import { currency, dayLabel, money, num } from '@/utils/format'
import { toast } from '@/toast'

const data = ref(null)
const showRecords = ref(false)
const series = [
  { key: 'cost', label: '消费', color: 'var(--chart-1)' },
  { key: 'recharge', label: '充值', color: 'var(--chart-2)' },
]

async function load() {
  try {
    data.value = await usageApi.adminOverview()
  } catch (e) {
    toast.error(e.message)
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
</style>
