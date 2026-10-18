import { exportUrl, http } from './http'

export const usageApi = {
  usageSummary: (query) => http.get('/api/usage/summary', query),
  usageLogs: (query) => http.get('/api/usage/logs', query),
  // The CSV is downloaded through a plain link, so this returns its URL instead of fetching it.
  usageExportUrl: (query) => exportUrl('/api/usage/export', query),
  overview: () => http.get('/api/admin/overview'),
}
