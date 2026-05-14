const API_BASE = import.meta.env.VITE_API_BASE || ''
const BUILD_TOKEN = import.meta.env.VITE_API_TOKEN || ''

function getToken() {
  if (typeof window !== 'undefined' && window.__ATRIUM_TOKEN__) return window.__ATRIUM_TOKEN__
  return BUILD_TOKEN
}

async function req(path, opts = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
    ...(opts.headers || {}),
  }
  const r = await fetch(`${API_BASE}${path}`, { ...opts, headers })
  if (!r.ok) {
    const text = await r.text().catch(() => '')
    throw new Error(`${r.status}: ${text}`)
  }
  if (r.status === 204) return null
  return r.json()
}

export const api = {
  health: () => req('/api/v1/health'),
  sessionInit: () => req('/api/v1/session/init'),
  getFocus: () => req('/api/v1/focus'),
  setFocus: (project_id) => req('/api/v1/focus', { method: 'POST', body: JSON.stringify({ current_project_id: project_id }) }),
  listProjects: (phase) => req(`/api/v1/projects${phase ? `?phase=${phase}` : ''}`),
  getProject: (id) => req(`/api/v1/projects/${id}`),
  patchProject: (id, patch) => req(`/api/v1/projects/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  createProject: (data) => req('/api/v1/projects', { method: 'POST', body: JSON.stringify(data) }),
  listTasks: (project_id) => req(`/api/v1/tasks${project_id ? `?project_id=${project_id}` : ''}`),
  createTask: (data) => req('/api/v1/tasks', { method: 'POST', body: JSON.stringify(data) }),
  patchTask: (id, patch) => req(`/api/v1/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  patchWorkbench: (id, patch) => req(`/api/v1/workbench/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  patchPattern: (id, patch) => req(`/api/v1/patterns/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  patchDecision: (id, patch) => req(`/api/v1/decisions/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  patchNote: (id, patch) => req(`/api/v1/notes/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  listComponents: (project_id) => req(`/api/v1/components${project_id ? `?project_id=${project_id}` : ''}`),
  createComponent: (data) => req('/api/v1/components', { method: 'POST', body: JSON.stringify(data) }),
  patchComponent: (id, patch) => req(`/api/v1/components/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  deleteComponent: (id) => req(`/api/v1/components/${id}`, { method: 'DELETE' }),
  listDecisions: (project_id) => req(`/api/v1/decisions${project_id ? `?project_id=${project_id}` : ''}`),
  createDecision: (data) => req('/api/v1/decisions', { method: 'POST', body: JSON.stringify(data) }),
  listNotes: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return req(`/api/v1/notes${q ? `?${q}` : ''}`)
  },
  createNote: (data) => req('/api/v1/notes', { method: 'POST', body: JSON.stringify(data) }),
  resolveNote: (id, summary) => req(`/api/v1/notes/${id}/resolve`, { method: 'POST', body: JSON.stringify({ summary }) }),
  listIntel: (target_type, target_id) => {
    const q = new URLSearchParams({ ...(target_type && { target_type }), ...(target_id && { target_id }) }).toString()
    return req(`/api/v1/intel${q ? `?${q}` : ''}`)
  },
  listWorkbench: (project_id) => {
    if (project_id) return req(`/api/v1/workbench?project_id=${project_id}`)
    return req('/api/v1/workbench')
  },
  createWorkbench: (data) => req('/api/v1/workbench', { method: 'POST', body: JSON.stringify(data) }),
  listEvents: (limit = 50) => req(`/api/v1/events?limit=${limit}`),
  listPatterns: (status) => req(`/api/v1/patterns${status ? `?status=${status}` : ''}`),
}

export function connectWS(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${window.location.host}/api/v1/ws/presence`
  const ws = new WebSocket(url)
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch (_) {}
  }
  ws.onclose = () => {
    setTimeout(() => connectWS(onMessage), 2000)
  }
  return ws
}
