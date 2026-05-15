const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function parseError(errorData) {
  if (errorData?.message) return errorData.message
  if (errorData?.detail) return errorData.detail
  return '请求失败，请稍后重试'
}

function getAccessToken() {
  return localStorage.getItem('aiops_token')
}

function getRefreshToken() {
  return localStorage.getItem('aiops_refresh_token')
}

function setAccessToken(token) {
  localStorage.setItem('aiops_token', token)
}

async function parseResponse(response) {
  if (!response.ok) {
    let message = '请求失败，请稍后重试'
    try {
      const errorData = await response.json()
      message = parseError(errorData)
    } catch {
      // ignore parse error
    }
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.text()
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    throw new Error('登录已过期，请重新登录')
  }

  const response = await fetch(`${apiBaseUrl}/api/refresh-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  const refreshed = await parseResponse(response)
  setAccessToken(refreshed.token)
  return refreshed.token
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, options)
  return parseResponse(response)
}

export async function apiGet(path, options = {}) {
  return apiRequest(path, { ...options, method: 'GET' })
}

export async function apiPost(path, data, options = {}) {
  return apiRequest(path, {
    ...options,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    body: JSON.stringify(data),
  })
}

export async function authorizedRequest(path, options = {}) {
  const currentToken = getAccessToken()
  if (!currentToken) {
    throw new Error('未登录，请先登录')
  }

  try {
    return await apiRequest(path, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${currentToken}`,
      },
    })
  } catch (error) {
    if (error.status !== 401) {
      throw error
    }

    const newToken = await refreshAccessToken()

    return apiRequest(path, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${newToken}`,
      },
    })
  }
}

export async function authorizedGet(path, options = {}) {
  return authorizedRequest(path, { ...options, method: 'GET' })
}

export async function authorizedPost(path, data, options = {}) {
  return authorizedRequest(path, {
    ...options,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    body: JSON.stringify(data),
  })
}
