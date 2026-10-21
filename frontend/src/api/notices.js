import { http } from './http'

export const noticesApi = {
  list: () => http.get('/api/notices'),
  create: (body) => http.post('/api/admin/notices', body),
  update: (id, body) => http.put(`/api/admin/notices/${id}`, body),
  remove: (id) => http.del(`/api/admin/notices/${id}`),
}
