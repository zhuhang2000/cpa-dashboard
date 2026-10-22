import { http } from './http'

export const settingsApi = {
  getStatus: () => http.get('/api/status'),

  adminGetSettings: () => http.get('/api/admin/settings'),
  adminPutSettings: (body) => http.put('/api/admin/settings', body),
  adminRunSync: () => http.post('/api/admin/sync'),
}
