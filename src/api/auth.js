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
  })
  return authorizedGet(`/api/alerts?${params.toString()}`)
}

export async function fetchAlertDetail(alertId) {
  return authorizedGet(`/api/alerts/${alertId}`)
}

export async function ackAlert(alertId) {
  return authorizedPost(`/api/alerts/${alertId}/ack`, {})
}

export async function silenceAlert(alertId) {
  return authorizedPost(`/api/alerts/${alertId}/silence`, {})
}

export async function assignAlert(alertId, assignee) {
  return authorizedPost(`/api/alerts/${alertId}/assign`, { assignee })
}

export function logout() {
  localStorage.removeItem('aiops_token')
  localStorage.removeItem('aiops_refresh_token')
  localStorage.removeItem('aiops_user')
}
