import { apiPost, authorizedGet, authorizedPost, authorizedRequest } from './client'

export async function login(payload) {
  return apiPost('/api/login', payload)
}

export async function fetchCurrentUser() {
  return authorizedGet('/api/me')
}

export async function changePassword(payload) {
  return authorizedPost('/api/change-password', payload)
}

export async function updateProfile(payload) {
  return authorizedPost('/api/profile', payload)
}

export async function uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)

  return authorizedRequest('/api/upload-avatar', {
    method: 'POST',
    body: formData,
  })
}

export async function fetchAlerts(filters) {
  const params = new URLSearchParams({
    level: filters.level,
    status: filters.status,
    service: filters.service,
    q: filters.q,
    page: String(filters.page ?? 1),
    page_size: String(filters.page_size ?? 10),
  })
  return authorizedGet(`/api/alerts?${params.toString()}`)
}

export async function fetchAlertDetail(alertId, filters = {}) {
  const params = new URLSearchParams()
  if (filters.action_operator) params.set('action_operator', filters.action_operator)
  if (filters.action_from) params.set('action_from', filters.action_from)
  if (filters.action_to) params.set('action_to', filters.action_to)
  if (filters.action_limit) params.set('action_limit', String(filters.action_limit))
  const query = params.toString()
  return authorizedGet(`/api/alerts/${alertId}${query ? `?${query}` : ''}`)
}

export async function ackAlert(alertId) {
  return authorizedPost(`/api/alerts/${alertId}/ack`, {})
}

export async function silenceAlert(alertId) {
  return authorizedPost(`/api/alerts/${alertId}/silence`, {})
}

export async function closeAlert(alertId) {
  return authorizedPost(`/api/alerts/${alertId}/close`, {})
}

export async function reopenAlert(alertId) {
  return authorizedPost(`/api/alerts/${alertId}/reopen`, {})
}

export async function assignAlert(alertId, assignee) {
  return authorizedPost(`/api/alerts/${alertId}/assign`, { assignee })
}

export function logout() {
  localStorage.removeItem('aiops_token')
  localStorage.removeItem('aiops_refresh_token')
  localStorage.removeItem('aiops_user')
}
