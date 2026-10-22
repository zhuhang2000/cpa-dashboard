import { http } from './http'

export const billingApi = {
  listTransactions: (query) => http.get('/api/billing/transactions', query),
  redeem: (body) => http.post('/api/billing/redeem', body),
  listOrders: (query) => http.get('/api/billing/orders', query),
  createOrder: (body) => http.post('/api/billing/orders', body),
  listUserTransactions: (userId, query) => http.get(`/api/admin/users/${userId}/transactions`, query),
  adjustBalance: (userId, body) => http.post(`/api/admin/users/${userId}/balance`, body),
  listCodes: (query) => http.get('/api/admin/codes', query),
  createCodes: (body) => http.post('/api/admin/codes', body),
  deleteCode: (code) => http.del(`/api/admin/codes/${encodeURIComponent(code)}`),
}
