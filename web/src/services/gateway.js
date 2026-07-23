const gatewayUrl = import.meta.env.VITE_RENTAL_API_URL?.replace(/\/$/, '')

function enabled() {
  return Boolean(gatewayUrl)
}

async function request(path, options = {}) {
  if (!enabled()) return null
  const response = await fetch(`${gatewayUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) throw new Error(`业务网关不可用 (${response.status})`)
  return response.json()
}

export async function recordConversation(userId, sessionId, role, content) {
  if (!sessionId || !content) return null
  return request('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, session_id: sessionId, role, content }),
  })
}

export async function loadConversation(userId, sessionId) {
  if (!sessionId) return []
  const result = await request(`/api/users/${encodeURIComponent(userId)}/conversations/${encodeURIComponent(sessionId)}`)
  return result?.items || []
}

export async function persistBooking(booking) {
  return request(`/api/bookings/${encodeURIComponent(booking.order_id)}`, {
    method: 'PUT',
    body: JSON.stringify(booking),
  })
}

export async function cancelPersistedBooking(userId, orderId) {
  return request(`/api/users/${encodeURIComponent(userId)}/bookings/${encodeURIComponent(orderId)}/cancel`, {
    method: 'POST',
  })
}
