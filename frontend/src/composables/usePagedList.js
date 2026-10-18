import { reactive } from 'vue'
import { toast } from '@/toast'

// State and loader for a paged list. `fetchPage` is a list endpoint from src/api (e.g.
// billingApi.listOrders) returning { items, total, page, page_size }; `query` returns the current
// filters. The whole response is merged into the state, so an endpoint that returns more fields
// (such as batches) can seed them through `extra`.
export function usePagedList(fetchPage, query = () => ({}), extra = {}) {
  const list = reactive({ items: [], total: 0, page: 1, page_size: 20, loading: false, ...extra, load })

  async function load(page = list.page) {
    list.loading = true
    try {
      Object.assign(list, await fetchPage({ ...query(), page }))
    } catch (e) {
      toast.error(e.message)
    } finally {
      list.loading = false
    }
  }

  return list
}
