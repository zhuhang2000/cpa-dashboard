import { http } from './http'

export const routingApi = {
  adminGetRouting: () => http.get('/api/admin/routing'),
  adminPutRouting: (body) => http.put('/api/admin/routing', body),
}
