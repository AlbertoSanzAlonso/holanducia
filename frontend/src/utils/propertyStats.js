function num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function median(values) {
  if (!values.length) return null
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
}

function avg(values) {
  if (!values.length) return null
  return values.reduce((a, b) => a + b, 0) / values.length
}

function normalizeSource(source) {
  return (source || 'Desconocido').trim() || 'Desconocido'
}

function pricePerM2(p) {
  const price = num(p.price)
  const size = num(p.size_m2)
  if (price == null || price <= 0 || size == null || size <= 0) return null
  return price / size
}

export function getUniqueSources(properties) {
  const values = new Set()
  for (const p of properties) {
    values.add(normalizeSource(p.source))
  }
  return [...values].sort((a, b) => a.localeCompare(b, 'es'))
}

export function computePropertyStats(properties, { sources = [] } = {}) {
  const sourceSet = sources.length ? new Set(sources.map(normalizeSource)) : null
  const items = properties.filter((p) => {
    if (sourceSet && !sourceSet.has(normalizeSource(p.source))) return false
    return true
  })

  const prices = items.map((p) => num(p.price)).filter((v) => v != null && v > 0)
  const m2Prices = items.map(pricePerM2).filter((v) => v != null)
  const sizes = items.map((p) => num(p.size_m2)).filter((v) => v != null && v > 0)
  const rooms = items.map((p) => num(p.rooms)).filter((v) => v != null && v > 0)
  const scores = items.map((p) => num(p.opportunity_score)).filter((v) => v != null)

  const bySourceMap = new Map()
  for (const p of items) {
    const src = normalizeSource(p.source)
    if (!bySourceMap.has(src)) {
      bySourceMap.set(src, { source: src, items: [] })
    }
    bySourceMap.get(src).items.push(p)
  }

  const bySource = [...bySourceMap.values()]
    .map(({ source, items: group }) => {
      const groupPrices = group.map((p) => num(p.price)).filter((v) => v != null && v > 0)
      const groupM2 = group.map(pricePerM2).filter((v) => v != null)
      const groupScores = group.map((p) => num(p.opportunity_score)).filter((v) => v != null)
      const particulars = group.filter((p) => p.is_individual).length
      return {
        source,
        count: group.length,
        avgPrice: avg(groupPrices),
        medianPrice: median(groupPrices),
        minPrice: groupPrices.length ? Math.min(...groupPrices) : null,
        maxPrice: groupPrices.length ? Math.max(...groupPrices) : null,
        avgM2Price: avg(groupM2),
        avgScore: avg(groupScores),
        particularCount: particulars,
        particularPct: group.length ? (particulars / group.length) * 100 : 0,
        hotCount: group.filter((p) => (p.opportunity_score ?? 0) >= 80).length,
      }
    })
    .sort((a, b) => b.count - a.count)

  const byCityMap = new Map()
  for (const p of items) {
    const city = (p.city || p.neighborhood || 'Sin ubicación').trim()
    if (!byCityMap.has(city)) byCityMap.set(city, [])
    byCityMap.get(city).push(p)
  }

  const byCity = [...byCityMap.entries()]
    .map(([city, group]) => {
      const groupPrices = group.map((p) => num(p.price)).filter((v) => v != null && v > 0)
      return { city, count: group.length, avgPrice: avg(groupPrices) }
    })
    .sort((a, b) => b.count - a.count)
    .slice(0, 8)

  const priceBuckets = [
    { label: '< 150k', min: 0, max: 150000, count: 0 },
    { label: '150–250k', min: 150000, max: 250000, count: 0 },
    { label: '250–350k', min: 250000, max: 350000, count: 0 },
    { label: '> 350k', min: 350000, max: Infinity, count: 0 },
  ]
  for (const price of prices) {
    const bucket = priceBuckets.find((b) => price >= b.min && price < b.max)
    if (bucket) bucket.count += 1
  }

  const opportunity = {
    hot: items.filter((p) => (p.opportunity_score ?? 0) >= 80).length,
    warm: items.filter((p) => {
      const s = p.opportunity_score ?? 0
      return s >= 60 && s < 80
    }).length,
    normal: items.filter((p) => (p.opportunity_score ?? 0) < 60).length,
  }

  const sellerType = {
    particular: items.filter((p) => p.is_individual).length,
    agency: items.filter((p) => p.is_agency && !p.is_individual).length,
    unknown: items.filter((p) => !p.is_individual && !p.is_agency).length,
  }

  const features = {
    parking: items.filter((p) => p.has_parking).length,
    terrace: items.filter((p) => p.has_terrace).length,
    pool: items.filter((p) => p.has_pool).length,
  }

  const topDeals = items
    .map((p) => ({ ...p, m2Price: pricePerM2(p) }))
    .filter((p) => p.m2Price != null)
    .sort((a, b) => a.m2Price - b.m2Price)
    .slice(0, 5)

  const maxSourceCount = bySource.length ? Math.max(...bySource.map((s) => s.count)) : 0

  return {
    total: items.length,
    withPrice: prices.length,
    withSize: sizes.length,
    avgPrice: avg(prices),
    medianPrice: median(prices),
    minPrice: prices.length ? Math.min(...prices) : null,
    maxPrice: prices.length ? Math.max(...prices) : null,
    avgM2Price: avg(m2Prices),
    medianM2Price: median(m2Prices),
    avgSize: avg(sizes),
    avgRooms: avg(rooms),
    avgScore: avg(scores),
    bySource,
    byCity,
    priceBuckets,
    opportunity,
    sellerType,
    features,
    topDeals,
    maxSourceCount,
  }
}
