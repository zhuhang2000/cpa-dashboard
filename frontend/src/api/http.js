// Thin fetch wrapper for the portal backend. Mutating requests carry
// X-Requested-With, which the backend requires as CSRF protection.
// Endpoints live in the sibling modules, one per backend router (backend/api/<name>.py), and each
// method is named after its handler (list_keys -> listKeys). Pages call those, never http directly.
export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

function buildUrl(path, query) {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== '') params.set(k, v)
  }
  const qs = params.toString()
  return qs ? `${path}?${qs}` : path
}

export async function request(method, path, { body, query, silent401 } = {}) {
  const headers = { Accept: 'application/json', 'X-Requested-With': 'portal' }
  const init = { method, headers, credentials: 'same-origin' }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }
  let res
  try {
    res = await fetch(buildUrl(path, query), init)
  } catch {
    throw new ApiError('网络连接失败，请检查网络后重试', 0)
  }
  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }
  if (!res.ok) {
    if (res.status === 401 && !silent401 && onUnauthorized) onUnauthorized()
    const message = (data && data.error) || `请求失败（HTTP ${res.status}）`
    throw new ApiError(message, res.status, data)
  }
  return data
}

export const http = {
  get: (path, query, opts) => request('GET', path, { query, ...opts }),
  post: (path, body) => request('POST', path, { body: body ?? {} }),
  put: (path, body) => request('PUT', path, { body: body ?? {} }),
  patch: (path, body) => request('PATCH', path, { body: body ?? {} }),
  del: (path, query) => request('DELETE', path, { query }),
}

export function exportUrl(path, query) {
  return buildUrl(path, query)
}
