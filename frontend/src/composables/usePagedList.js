import { reactive } from 'vue'
import { api } from '@/api'
import { toast } from '@/toast'

// State and loader for a paged list endpoint, which returns { items, total, page, page_size }.
// `query` returns the current filters. The whole response is merged into the state, so an
// endpoint that returns more fields (such as batches) can seed them through `extra`.
export function usePagedList(path, query = () => ({}), extra = {}) {
  const list = reactive({ items: [], total: 0, page: 1, page_size: 20, loading: false, ...extra, load })

  async function load(page = list.page) {
    list.loading = true
    try {
      Object.assign(list, await api.get(path, { ...query(), page }))
    } catch (e) {
      toast.error(e.message)
    } finally {
      list.loading = false
    }
  }

  return list
}
