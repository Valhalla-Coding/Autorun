const BASE = ''

function getToken() { return localStorage.getItem('autorun_token') }
function setToken(t) { t ? localStorage.setItem('autorun_token', t) : localStorage.removeItem('autorun_token') }

async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const opts = { method, headers }
  if (body !== null) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  if (res.status === 401) setToken(null)
  const data = await res.json().catch(() => ({ status: 'error', error: { message: 'Invalid response' } }))
  if (!res.ok) throw new ApiError(data?.error?.message || `HTTP ${res.status}`, res.status, data)
  return data
}

export class ApiError extends Error {
  constructor(message, status, data) { super(message); this.status = status; this.data = data }
}

export const auth = {
  login: (username, password) => request('POST', '/api/auth/login', { username, password })
    .then(d => { setToken(d.data.token); return d }),
  logout: () => request('POST', '/api/auth/logout').finally(() => setToken(null)),
  me: () => request('GET', '/api/auth/me'),
}

export const services = {
  list:    ()           => request('GET',    '/api/services'),
  get:     (name)       => request('GET',    `/api/services/${name}`),
  create:  (body)       => request('POST',   '/api/services', body),
  update:  (name, body) => request('PUT',    `/api/services/${name}`, body),
  delete:  (name)       => request('DELETE', `/api/services/${name}`),
  start:   (name)       => request('POST',   `/api/services/${name}/start`),
  stop:    (name)       => request('POST',   `/api/services/${name}/stop`),
  restart: (name)       => request('POST',   `/api/services/${name}/restart`),
  pull:    (name)       => request('POST',   `/api/services/${name}/pull`),
  enable:  (name)       => request('POST',   `/api/services/${name}/enable`),
  disable: (name)       => request('POST',   `/api/services/${name}/disable`),
}

export const system = {
  status:        ()     => request('GET',  '/api/system/status'),
  daemonReload:  ()     => request('POST', '/api/system/daemon-reload'),
  health:        ()     => request('GET',  '/api/health'),
  browseFolders: (path) => request('GET',  `/api/browse/folders${path ? `?path=${encodeURIComponent(path)}` : ''}`),
  browseFiles:   (path) => request('GET',  `/api/browse/files?path=${encodeURIComponent(path)}`),
}

export const github = {
  repoInfo: (url) => request('GET', `/api/github/repo-info?url=${encodeURIComponent(url)}`),
}

export const settings = {
  get:    ()     => request('GET', '/api/settings'),
  update: (body) => request('PUT', '/api/settings', body),
}

export { getToken, setToken }
