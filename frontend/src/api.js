const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:9000'

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `HTTP ${response.status}`)
  }

  if (response.status === 204) return null
  return response.json()
}

export const api = {
  getProperties: () => request('/api/properties'),
  getCategories: () => request('/api/categories'),
  updateProperty: (id, data) => request(`/api/properties/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProperty: (id) => request(`/api/properties/${id}`, { method: 'DELETE' }),
  deleteProperties: (ids) => request('/api/properties/batch-delete', { method: 'POST', body: JSON.stringify({ ids }) }),
  updatePropertiesCategory: (ids, category_id) =>
    request('/api/properties/batch-category', { method: 'POST', body: JSON.stringify({ ids, category_id }) }),
  getSettings: () => request('/api/settings'),
  saveSettings: (data) => request('/api/settings', { method: 'PUT', body: JSON.stringify(data) }),
  createScrapingRequest: (data) => request('/api/scraping-requests', { method: 'POST', body: JSON.stringify(data) }),
  getLatestScrapingRequest: () => request('/api/scraping-requests/latest'),
}
