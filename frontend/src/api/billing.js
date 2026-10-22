import { http } from './http'

export const billingApi = {
  listTransactions: (query) => http.get('/api/billing/transactions', query),
  redeem: (body) => http.post('/api/billing/redeem', body),
  listOrders: (query) => http.get('/api/billing/orders', query),
  createOrder: (body) => http.post('/api/billing/orders', body),

  adminListTransactions: (userId, query) => http.get(`/api/admin/users/${userId}/billing/transactions`, query),
  adminAdjustBalance: (userId, body) => http.post(`/api/admin/users/${userId}/balance`, body),
  adminListCodes: (query) => http.get('/api/admin/codes', query),
  adminCreateCodes: (body) => http.post('/api/admin/codes', body),
  adminDeleteCode: (code) => http.del(`/api/admin/codes/${encodeURIComponent(code)}`),
}
