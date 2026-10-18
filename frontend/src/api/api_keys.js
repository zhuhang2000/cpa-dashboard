import { http } from './http'

export const keysApi = {
  listKeys: () => http.get('/api/keys'),
  createKey: (body) => http.post('/api/keys', body),
  updateKey: (id, body) => http.patch(`/api/keys/${id}`, body),
  deleteKey: (id) => http.del(`/api/keys/${id}`),
  revealKey: (id) => http.post(`/api/keys/${id}/reveal`),
}
