import { http } from './http'

export const pricingApi = {
  listPrices: () => http.get('/api/prices'),

  adminListPrices: () => http.get('/api/admin/prices'),
  adminUpsertPrice: (body) => http.put('/api/admin/prices', body),
  adminDeletePrice: (body) => http.post('/api/admin/prices/delete', body),
  adminSetVisibility: (body) => http.post('/api/admin/prices/visibility', body),
}
