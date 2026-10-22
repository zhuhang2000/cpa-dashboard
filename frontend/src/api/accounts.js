import { http } from './http'

export const accountsApi = {
  register: (body) => http.post('/api/auth/register', body),
  login: (body) => http.post('/api/auth/login', body),
  logout: () => http.post('/api/auth/logout'),
  // A 401 here only means "not signed in", so it must not trigger the session-expired redirect.
  getMe: () => http.get('/api/user/me', null, { silent401: true }),
  updateProfile: (body) => http.put('/api/user/profile', body),
  changePassword: (body) => http.post('/api/user/password', body),
  listUsers: (query) => http.get('/api/admin/users', query),
  archiveUsers: (body) => http.post('/api/admin/users/archive', body),
  setUserStatus: (id, body) => http.put(`/api/admin/users/${id}/status`, body),
  setUserRole: (id, body) => http.put(`/api/admin/users/${id}/role`, body),
  resetPassword: (id, body) => http.post(`/api/admin/users/${id}/password`, body),
}
