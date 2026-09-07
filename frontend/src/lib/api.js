const BASE = '/api'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  let data = null
  try {
    data = await res.json()
  } catch {}

  if (!res.ok) {
    const detail = data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg ?? JSON.stringify(d)).join('; ')
          : `Request failed (${res.status})`
    throw new ApiError(message, res.status)
  }

  return data
}

export const api = {
  setupStatus: () => request('GET', '/setup/status'),
  setupIcloud: (body) => request('POST', '/setup/icloud', body),
  setupMosque: (body) => request('POST', '/setup/mosque', body),

  getConfig: () => request('GET', '/config'),
  updateIcloud: (body) => request('PUT', '/config/icloud', body),
  updateMosque: (body) => request('PUT', '/config/mosque', body),
  updatePrayers: (body) => request('PUT', '/config/prayers', body),
  updateSchedule: (body) => request('PUT', '/config/schedule', body),

  todayPrayerTimes: () => request('GET', '/prayer-times/today'),
  syncStatus: () => request('GET', '/sync/status'),
  syncRun: () => request('POST', '/sync/run'),
}
