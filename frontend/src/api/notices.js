import { http } from './http'

export const noticesApi = {
  listNotices: () => http.get('/api/notices'),

  adminCreateNotice: (body) => http.post('/api/admin/notices', body),
  adminUpdateNotice: (id, body) => http.put(`/api/admin/notices/${id}`, body),
  adminDeleteNotice: (id) => http.del(`/api/admin/notices/${id}`),
}
