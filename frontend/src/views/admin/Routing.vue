<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">节点分流</h1>
        <p class="page-desc">按 API Key 把用户分到各 CPA 节点。保存后几秒内生效，不需要 reload nginx。</p>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="syncing" @click="sync">
          <Icon :name="syncing ? 'loader' : 'refresh'" :size="16" />立即同步
        </button>
      </div>
    </div>

    <template v-if="data">
      <div v-if="!data.nginx.configured" class="alert alert-warning">
        <Icon name="alert" :size="16" />
        <div class="alert-body">
          未配置分流控制接口：这里的设置只会保存，不会生效，也看不到实时数据。在
          <code>backend/core/.env</code> 中填写 <code>ROUTER_CONTROL_URL</code> 和
          <code>ROUTER_CONTROL_TOKEN</code> 后重启 Portal。
        </div>
      </div>
      <div v-else-if="data.nginx.error" class="alert alert-danger">
        <Icon name="alert" :size="16" />
        <div class="alert-body">
          <b>分流配置未能下发：</b>{{ data.nginx.error }}。设置已保存，同步任务每
          {{ data.nginx.sync_interval_seconds }} 秒重试一次。
        </div>
      </div>
      <div v-else-if="data.nginx.applied === false" class="alert alert-info">
        <Icon name="info" :size="16" />
        <div class="alert-body">
          nginx 当前的分流配置与保存的设置不一致（nginx 重启后会出现），同步任务会在
          {{ data.nginx.sync_interval_seconds }} 秒内重新下发。
        </div>
      </div>

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
    </template>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">分流设置</div>
          <div class="card-sub">实时数据每 {{ POLL_SECONDS }} 秒刷新</div>
        </div>
        <span v-if="data" class="badge" :class="appliedBadge.tone">{{ appliedBadge.label }}</span>
      </div>
      <div v-if="!form" class="card-body stack" style="gap: 12px">
        <div v-for="i in 3" :key="i" class="skeleton" style="height: 38px" />
      </div>
      <template v-else>
        <div class="card-body">
          <label class="toggle">
            <input v-model="form.enabled" type="checkbox" />
            <span class="toggle-track" />
            开启分流
          </label>
          <div class="field-hint">
            <template v-if="form.enabled">
              新用户分给“活跃用户数 ÷ 容量比例”最低的节点；同一个 API Key 10 分钟内固定在一个节点上。
            </template>
            <template v-else>关闭时所有请求都走 {{ firstNode }}，{{ firstNode }} 连不上时才转给备用节点。</template>
          </div>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>节点</th>
                <th>参与分流</th>
                <th>容量比例</th>
                <th class="right">新用户占比</th>
                <th class="right">活跃用户</th>
                <th class="right">处理中</th>
                <th class="right">今日请求</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="node in form.nodes" :key="node.id">
                <td>
                  <div class="cell-main">{{ node.id }}</div>
                  <div class="cell-sub">
                    <span v-if="live(node.id)?.down" class="text-danger">故障中，暂不分配新用户</span>
                    <span v-else-if="live(node.id)">在线</span>
                    <span v-else>—</span>
                  </div>
                </td>
                <td>
                  <label class="toggle">
                    <input v-model="node.enabled" type="checkbox" :aria-label="`${node.id} 参与分流`" />
                    <span class="toggle-track" />
                  </label>
                </td>
                <td>
                  <input
                    v-model.number="node.capacity"
                    class="input input-sm capacity"
                    type="number"
                    min="0.01"
                    :max="MAX_CAPACITY"
                    step="any"
                    :aria-label="`${node.id} 容量比例`"
                  />
                </td>
                <td class="right num">{{ share(node) }}</td>
                <td class="right num">{{ stat(node.id, 'users') }}</td>
                <td class="right num">{{ stat(node.id, 'inflight') }}</td>
                <td class="right num">{{ stat(node.id, 'today') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="card-footer row-between">
          <span class="field-hint" :class="{ 'text-danger': problem }" style="margin: 0">
            {{
              problem ||
              '容量比例是相对值：2 和 1 表示新用户按 2 : 1 分配。停用的节点上已有的用户会在下次请求时改到其他节点。'
            }}
          </span>
          <span class="row">
            <button class="btn" :disabled="!dirty || saving" @click="reset">撤销</button>
            <button class="btn btn-primary" :disabled="!dirty || saving || Boolean(problem)" @click="save">
              {{ saving ? '保存中…' : '保存并生效' }}
            </button>
          </span>
        </div>
      </template>
    </div>

    <div class="card">
      <div class="card-header"><div class="card-title">同步状态</div></div>
      <div v-if="!data" class="card-body">
        <div class="skeleton" style="height: 160px" />
      </div>
      <div v-else class="card-body grid grid-2" style="align-items: start">
        <div v-for="node in data.nodes" :key="node.id" class="sync-block">
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Icon from '@/components/base/Icon.vue'
import { routingApi } from '@/api/routing'
import { settingsApi } from '@/api/settings'
import { dateTime, num } from '@/utils/format'
import { toast } from '@/toast'

// Matches services/routing.py.
const MAX_CAPACITY = 1000
const POLL_SECONDS = 5

const data = ref(null)
// Edited copy of data.routing; polling refreshes the live numbers without touching it.
const form = ref(null)
const saving = ref(false)
const syncing = ref(false)
let timer = null

const copy = (routing) => JSON.parse(JSON.stringify(routing))
const dirty = computed(() => Boolean(form.value) && JSON.stringify(form.value) !== JSON.stringify(data.value.routing))
const firstNode = computed(() => form.value?.nodes[0]?.id || 'node1')
const participating = computed(() => form.value?.nodes.filter((node) => node.enabled) || [])

const problem = computed(() => {
  if (!form.value) return ''
  // The backend checks every node, participating or not.
  const bad = form.value.nodes.find(
    (node) => !(typeof node.capacity === 'number' && node.capacity > 0 && node.capacity <= MAX_CAPACITY),
  )
  if (bad) return `${bad.id} 的容量比例需大于 0 且不超过 ${MAX_CAPACITY}`
  if (form.value.enabled && !participating.value.length) return '开启分流时至少要有一个节点参与分流'
  return ''
})

const appliedBadge = computed(() => {
  const nginx = data.value.nginx
  if (!nginx.configured) return { label: '未接入 nginx', tone: '' }
  if (nginx.applied === true)
    return { label: data.value.routing.enabled ? '已生效 · 分流中' : '已生效 · 分流关闭', tone: 'badge-success' }
  if (nginx.applied === false) return { label: '等待下发', tone: 'badge-warning' }
  return { label: '无法连接 nginx', tone: 'badge-danger' }
})

function live(id) {
  return data.value?.nginx.nodes[id]
}
function stat(id, key) {
  const item = live(id)
  return item ? num(item[key]) : '—'
}

// Share of new users each node would get with the settings being edited.
function share(node) {
  if (!form.value.enabled) return node.id === firstNode.value ? '全部' : '—'
  if (!node.enabled) return '—'
  const total = participating.value.reduce((sum, item) => sum + (Number(item.capacity) || 0), 0)
  if (!total || !(node.capacity > 0)) return '—'
  return `${Math.round((node.capacity / total) * 100)}%`
}

function badge(ok) {
  return ok === true ? 'badge-success' : ok === false ? 'badge-danger' : ''
}
function label(ok) {
  return ok === true ? '正常' : ok === false ? '异常' : '等待中'
}

function show(result) {
  const keepEdits = dirty.value
  data.value = result
  if (!keepEdits) form.value = copy(result.routing)
}

async function load({ quiet = false } = {}) {
  try {
    show(await routingApi.adminGetRouting())
  } catch (e) {
    if (!quiet) toast.error(e.message)
  }
}

function reset() {
  form.value = copy(data.value.routing)
}

async function save() {
  saving.value = true
  try {
    const result = await routingApi.adminPutRouting(form.value)
    data.value = result
    form.value = copy(result.routing)
    if (!result.nginx.configured) toast.info('已保存，未配置分流控制接口，暂不生效')
    else if (result.nginx.applied) toast.success('已保存并生效')
    else toast.error('已保存，但未能下发到 nginx，同步任务会自动重试')
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
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

onMounted(() => {
  load()
  timer = setInterval(() => {
    if (document.visibilityState === 'visible' && !saving.value) load({ quiet: true })
  }, POLL_SECONDS * 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.capacity {
  width: 96px;
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
