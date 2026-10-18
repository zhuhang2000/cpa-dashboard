import { http } from './http'

export const pricingApi = {
  getPricing: () => http.get('/api/pricing'),
  listPrices: () => http.get('/api/admin/prices'),
  upsertPrice: (body) => http.put('/api/admin/prices', body),
  deletePrice: (body) => http.post('/api/admin/prices/delete', body),
  setVisibility: (body) => http.post('/api/admin/prices/visibility', body),
}
