import { http } from './http'

export const settingsApi = {
  getStatus: () => http.get('/api/status'),
  getSettings: () => http.get('/api/admin/settings'),
  putSettings: (body) => http.put('/api/admin/settings', body),
  runSync: () => http.post('/api/admin/sync'),
}
