/** Precio legible: 0 o vacío → "Sin determinar". */
export function formatPrice(price) {
  const n = Number(price)
  if (!Number.isFinite(n) || n <= 0) return 'Sin determinar'
  return `${n.toLocaleString('es-ES')}€`
}

/** URL del anuncio original. Para FB sin permalink, enlace al grupo. */
export function getListingUrl(property) {
  const url = (property?.url || '').trim()
  if (!url) return null

  if (url.startsWith('http')) {
    if (url.includes('facebook.com')) {
      if (url.includes('#lead-')) {
        const groupUrl = url.split('#')[0].replace(/\/$/, '')
        return groupUrl.includes('/groups/') ? groupUrl : null
      }
      return url.split('#')[0]
    }
    if (!url.includes('#lead-')) return url
  }

  return null
}

/** Resuelve rutas relativas de imágenes al proxy /api. */
export function resolveImageUrl(src) {
  if (!src) return null
  if (src.startsWith('http://') || src.startsWith('https://')) return src
  if (src.startsWith('/api/')) return src
  if (src.startsWith('/')) return src
  return `/api/media/properties/${src.replace(/^\//, '')}`
}

export function hasPropertyImage(property) {
  const src = resolveImageUrl(property?.images?.[0])
  if (!src) return false
  return !src.includes('unsplash.com')
}
