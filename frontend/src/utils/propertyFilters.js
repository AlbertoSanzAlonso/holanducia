export const SORT_OPTIONS = [
  { value: 'newest', label: 'Más recientes' },
  { value: 'oldest', label: 'Más antiguos' },
  { value: 'price_asc', label: 'Precio ↑' },
  { value: 'price_desc', label: 'Precio ↓' },
  { value: 'score_desc', label: 'Mejor oportunidad' },
]

export const DEFAULT_FILTERS = {
  title: '',
  city: '',
  sources: [],
  minPrice: '',
  maxPrice: '',
  sort: 'newest',
}

function parsePrice(value) {
  if (value === '' || value == null) return null
  const n = Number(String(value).replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

function propertyPrice(p) {
  const n = Number(p?.price)
  return Number.isFinite(n) && n > 0 ? n : null
}

function propertyDate(p) {
  const raw = p?.created_at || p?.updated_at
  return raw ? new Date(raw).getTime() : 0
}

export function getUniqueSources(properties) {
  const values = new Set()
  for (const p of properties) {
    const source = (p.source || '').trim()
    if (source) values.add(source)
  }
  return [...values].sort((a, b) => a.localeCompare(b, 'es'))
}

export function getUniqueCities(properties) {
  const values = new Set()
  for (const p of properties) {
    const city = (p.city || '').trim()
    const neighborhood = (p.neighborhood || '').trim()
    if (city) values.add(city)
    if (neighborhood && neighborhood !== city) values.add(neighborhood)
  }
  return [...values].sort((a, b) => a.localeCompare(b, 'es'))
}

export function countActiveFilters(filters) {
  let n = 0
  if (filters.title?.trim()) n += 1
  if (filters.city) n += 1
  if (filters.sources?.length > 0) n += 1
  if (filters.minPrice !== '' && filters.minPrice != null) n += 1
  if (filters.maxPrice !== '' && filters.maxPrice != null) n += 1
  if (filters.sort && filters.sort !== 'newest') n += 1
  return n
}

export function applyPropertyFilters(properties, filters, { filter = 'all', selectedCategoryId = null, listPropertyIds = null } = {}) {
  const titleQ = (filters.title || '').trim().toLowerCase()
  const minP = parsePrice(filters.minPrice)
  const maxP = parsePrice(filters.maxPrice)
  const sourceSet = filters.sources?.length ? new Set(filters.sources) : null
  const listSet = listPropertyIds ? new Set(listPropertyIds) : null

  let result = properties.filter((p) => {
    if (listSet && !listSet.has(p.id)) return false
    if (selectedCategoryId && p.category_id !== selectedCategoryId) return false
    if (filter === 'hot' && (p.opportunity_score ?? 0) < 80) return false
    if (filter === 'particular' && !p.is_individual) return false

    if (sourceSet) {
      const source = (p.source || '').trim()
      if (!sourceSet.has(source)) return false
    }

    if (titleQ) {
      const haystack = [p.title, p.description, p.neighborhood, p.address]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      if (!haystack.includes(titleQ)) return false
    }

    if (filters.city) {
      const city = (p.city || '').trim()
      const neighborhood = (p.neighborhood || '').trim()
      if (city !== filters.city && neighborhood !== filters.city) return false
    }

    const price = propertyPrice(p)
    if (minP != null) {
      if (price == null || price < minP) return false
    }
    if (maxP != null) {
      if (price == null || price > maxP) return false
    }

    return true
  })

  const sort = filters.sort || 'newest'
  result = [...result].sort((a, b) => {
    switch (sort) {
      case 'oldest':
        return propertyDate(a) - propertyDate(b)
      case 'price_asc': {
        const pa = propertyPrice(a)
        const pb = propertyPrice(b)
        if (pa == null && pb == null) return 0
        if (pa == null) return 1
        if (pb == null) return -1
        return pa - pb
      }
      case 'price_desc': {
        const pa = propertyPrice(a)
        const pb = propertyPrice(b)
        if (pa == null && pb == null) return 0
        if (pa == null) return 1
        if (pb == null) return -1
        return pb - pa
      }
      case 'score_desc':
        return (b.opportunity_score ?? 0) - (a.opportunity_score ?? 0)
      case 'newest':
      default:
        return propertyDate(b) - propertyDate(a)
    }
  })

  return result
}
