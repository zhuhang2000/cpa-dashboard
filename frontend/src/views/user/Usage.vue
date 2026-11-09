<template>
  <div class="stack">
    <div class="page-header">
      <div>
        <h1 class="page-title">用量明细</h1>
        <p class="page-desc">每一次调用的模型、tokens 与费用。数据通常在请求完成后 15 秒内出现。</p>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="loading" @click="load"><Icon name="refresh" :size="16" />刷新</button>
        <a class="btn" :href="exportHref" download><Icon name="download" :size="16" />导出 CSV</a>
      </div>
    </div>

    <div class="card">
      <UsageFilters v-model="filters" :keys="keys" :models="data.models" @change="apply" />
      <div class="summary-bar">
        <span
          >请求 <b class="num">{{ num(data.total) }}</b> 次</span
        >
        <span
          >消费 <b class="num">{{ money(data.sum_cost) }}</b></span
        >
        <span
          >Tokens <b class="num">{{ tokens(data.sum_tokens) }}</b></span
        >
      </div>
      <div v-if="loading && !data.items.length" class="card-body stack" style="gap: 10px">
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 34px" />
      </div>
      <EmptyState
        v-else-if="!data.items.length"
        icon="activity"
        title="没有符合条件的调用记录"
        desc="调整筛选条件，或使用 API 密钥发起一次调用"
      />
      <UsageLogTable v-else :items="data.items" />
      <div v-if="data.total" class="card-footer">
        <Pagination :page="page" :total="data.total" :page-size="pageSize" @change="go" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import EmptyState from '@/components/base/EmptyState.vue'
import Icon from '@/components/base/Icon.vue'
import Pagination from '@/components/base/Pagination.vue'
import UsageFilters, { usageFilters, usageQuery } from '@/components/shared/UsageFilters.vue'
import UsageLogTable from '@/components/shared/UsageLogTable.vue'
import { keysApi } from '@/api/api_keys'
import { usageApi } from '@/api/usage'
import { money, num, tokens } from '@/utils/format'
import { toast } from '@/toast'

const filters = ref(usageFilters())
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const keys = ref([])
const data = reactive({ items: [], total: 0, sum_cost: 0, sum_tokens: 0, models: [] })

const exportHref = computed(() => usageApi.usageExportUrl(usageQuery(filters.value)))

async function load() {
  loading.value = true
  try {
    Object.assign(
      data,
      await usageApi.usageLogs({ ...usageQuery(filters.value), page: page.value, page_size: pageSize }),
    )
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function apply() {
  page.value = 1
  load()
}
function go(p) {
  page.value = p
  load()
}

onMounted(async () => {
  load()
  try {
    keys.value = (await keysApi.listKeys()).items
  } catch {
    /* filter list is optional */
  }
})
</script>
