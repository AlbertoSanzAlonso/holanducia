import { useMemo, useState, useEffect } from 'react'
import {
  BarChart3, Building2, Flame, Home, MapPin, TrendingDown, TrendingUp, Users, Wallet,
} from 'lucide-react'
import { formatPrice } from './utils/propertyDisplay'
import { computePropertyStats, computeTopDeals, getUniqueSources, getZoneOptions } from './utils/propertyStats'

const SOURCE_COLORS = {
  Facebook: '#1877F2',
  'pisos.com': '#e11d48',
  'fotocasa.es': '#00a8e8',
  'habitaclia.com': '#f97316',
  Fotocasa: '#00a8e8',
  Habitaclia: '#f97316',
  'Pisos.com': '#e11d48',
}

function sourceColor(source) {
  return SOURCE_COLORS[source] || '#6366f1'
}

function fmtNum(n, digits = 0) {
  if (n == null || !Number.isFinite(n)) return '—'
  return n.toLocaleString('es-ES', { maximumFractionDigits: digits })
}

export default function StatisticsView({ properties = [], onPropertySelect }) {
  const allSources = useMemo(() => getUniqueSources(properties), [properties])
  const [selectedSources, setSelectedSources] = useState([])
  const [topDealsZone, setTopDealsZone] = useState('')

  const stats = useMemo(
    () => computePropertyStats(properties, { sources: selectedSources }),
    [properties, selectedSources]
  )

  const zoneOptions = useMemo(
    () => getZoneOptions(properties, { sources: selectedSources }),
    [properties, selectedSources]
  )

  const topDeals = useMemo(
    () => computeTopDeals(properties, { sources: selectedSources, zone: topDealsZone, limit: 5 }),
    [properties, selectedSources, topDealsZone]
  )

  useEffect(() => {
    if (topDealsZone && !zoneOptions.includes(topDealsZone)) {
      setTopDealsZone('')
    }
  }, [zoneOptions, topDealsZone])

  const toggleSource = (source) => {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]
    )
  }

  if (!properties.length) {
    return (
      <div className="p-12 text-slate-400 font-medium italic">
        No hay propiedades para analizar. Ejecuta un scraping desde Configuración.
      </div>
    )
  }

  return (
    <section className="bg-white p-6 lg:p-16 min-h-screen">
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-3 rounded-2xl bg-[#0f172a] text-white">
            <BarChart3 size={22} />
          </div>
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-[#00acee]">Inteligencia de mercado</p>
        </div>
        <h2 className="text-4xl lg:text-5xl font-black text-slate-900 tracking-tight">Estadísticas</h2>
        <p className="text-slate-400 text-sm mt-3 font-bold uppercase tracking-[0.2em]">
          {stats.total} ofertas analizadas
          {selectedSources.length > 0 ? ` · ${selectedSources.length} fuente(s) seleccionada(s)` : ' · todas las fuentes'}
        </p>
      </div>

      {allSources.length > 1 && (
        <div className="mb-12 p-6 rounded-[2rem] border border-slate-100 bg-slate-50/80">
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Filtrar por fuente</p>
          <div className="flex flex-wrap gap-2">
            <SourceChip
              label="Todas"
              active={selectedSources.length === 0}
              color="#0f172a"
              onClick={() => setSelectedSources([])}
            />
            {allSources.map((src) => (
              <SourceChip
                key={src}
                label={src}
                count={properties.filter((p) => (p.source || 'Desconocido').trim() === src).length}
                active={selectedSources.includes(src)}
                color={sourceColor(src)}
                onClick={() => toggleSource(src)}
              />
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-12">
        <KpiCard icon={<Home size={20} />} label="Ofertas" value={stats.total} />
        <KpiCard icon={<Wallet size={20} />} label="Precio medio" value={formatPrice(stats.avgPrice)} sub={`Mediana ${formatPrice(stats.medianPrice)}`} />
        <KpiCard icon={<TrendingUp size={20} />} label="€/m² medio" value={stats.avgM2Price ? `${fmtNum(stats.avgM2Price)} €/m²` : '—'} sub={stats.withSize ? `${stats.withSize} con m²` : ''} />
        <KpiCard icon={<Flame size={20} />} label="TOP oportunidades" value={stats.opportunity.hot} sub={`Score ≥ 80 · media ${fmtNum(stats.avgScore, 1)}`} accent="orange" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-12">
        <Panel title="Comparativa por fuente" icon={<Building2 size={18} />}>
          {stats.bySource.length === 0 ? (
            <EmptyPanel />
          ) : (
            <div className="space-y-5">
              {stats.bySource.map((row) => (
                <div key={row.source}>
                  <div className="flex justify-between items-end mb-2 gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-black text-slate-900 truncate">{row.source}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        {row.count} anuncios · {row.hotCount} TOP · {fmtNum(row.particularPct, 0)}% particulares
                      </p>
                    </div>
                    <p className="text-sm font-black text-slate-700 shrink-0">{formatPrice(row.avgPrice)}</p>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${stats.maxSourceCount ? (row.count / stats.maxSourceCount) * 100 : 0}%`,
                        backgroundColor: sourceColor(row.source),
                      }}
                    />
                  </div>
                  <div className="flex gap-4 mt-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <span>€/m²: {row.avgM2Price ? `${fmtNum(row.avgM2Price)} €` : '—'}</span>
                    <span>Min: {formatPrice(row.minPrice)}</span>
                    <span>Max: {formatPrice(row.maxPrice)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Distribución de precios" icon={<Wallet size={18} />}>
          <div className="space-y-4">
            {stats.priceBuckets.map((bucket) => {
              const pct = stats.withPrice ? (bucket.count / stats.withPrice) * 100 : 0
              return (
                <div key={bucket.label}>
                  <div className="flex justify-between mb-1.5">
                    <span className="text-xs font-black text-slate-700">{bucket.label}</span>
                    <span className="text-xs font-bold text-slate-400">{bucket.count} ({fmtNum(pct, 0)}%)</span>
                  </div>
                  <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[#00acee] rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-8 pt-6 border-t border-slate-100 grid grid-cols-2 gap-4">
            <MiniStat label="Precio mínimo" value={formatPrice(stats.minPrice)} />
            <MiniStat label="Precio máximo" value={formatPrice(stats.maxPrice)} />
            <MiniStat label="Tamaño medio" value={stats.avgSize ? `${fmtNum(stats.avgSize, 0)} m²` : '—'} />
            <MiniStat label="Habitaciones med." value={stats.avgRooms ? fmtNum(stats.avgRooms, 1) : '—'} />
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-12">
        <Panel title="Precio medio por zona" icon={<MapPin size={18} />}>
          {stats.byZone.length === 0 ? (
            <EmptyPanel />
          ) : (
            <div className="space-y-5">
              {stats.byZone.map((row) => (
                <div key={row.zone}>
                  <div className="flex justify-between items-end mb-2 gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-black text-slate-900 truncate">{row.zone}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        {row.count} ofertas · mediana {formatPrice(row.medianPrice)}
                      </p>
                    </div>
                    <p className="text-sm font-black text-[#00acee] shrink-0">{formatPrice(row.avgPrice)}</p>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#00acee] rounded-full transition-all duration-700"
                      style={{
                        width: `${stats.maxZoneCount ? (row.count / stats.maxZoneCount) * 100 : 0}%`,
                      }}
                    />
                  </div>
                  {row.avgM2Price != null && (
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-2">
                      €/m² medio: {fmtNum(row.avgM2Price)} €
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Oportunidades por zona" icon={<Flame size={18} />}>
          {stats.byZone.length === 0 ? (
            <EmptyPanel />
          ) : (
            <div className="space-y-5">
              {[...stats.byZone]
                .sort((a, b) => b.hotCount - a.hotCount || b.avgScore - a.avgScore)
                .map((row) => (
                  <div key={`hot-${row.zone}`}>
                    <div className="flex justify-between items-end mb-2 gap-4">
                      <div className="min-w-0">
                        <p className="text-sm font-black text-slate-900 truncate">{row.zone}</p>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          {row.hotCount} TOP · {row.warmCount} interesantes · score {fmtNum(row.avgScore, 1)}
                        </p>
                      </div>
                      <p className="text-sm font-black text-orange-500 shrink-0">
                        {fmtNum(row.hotPct, 0)}% TOP
                      </p>
                    </div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden flex">
                      <div
                        className="h-full bg-orange-500 rounded-l-full transition-all duration-700"
                        style={{
                          width: `${stats.maxZoneHot ? (row.hotCount / stats.maxZoneHot) * 100 : 0}%`,
                        }}
                      />
                      <div
                        className="h-full bg-[#00acee] transition-all duration-700"
                        style={{
                          width: `${stats.maxZoneHot ? (row.warmCount / stats.maxZoneHot) * 60 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 mb-12">
        <Panel title="Resumen por zona" icon={<MapPin size={18} />} className="xl:col-span-3">
          {stats.byZone.length === 0 ? (
            <EmptyPanel />
          ) : (
            <div className="overflow-x-auto -mx-2">
              <table className="w-full min-w-[720px] text-left">
                <thead>
                  <tr className="text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100">
                    <th className="py-4 px-3">Zona</th>
                    <th className="py-4 px-3 text-right">Ofertas</th>
                    <th className="py-4 px-3 text-right">Precio medio</th>
                    <th className="py-4 px-3 text-right">Mediana</th>
                    <th className="py-4 px-3 text-right">€/m²</th>
                    <th className="py-4 px-3 text-right">TOP (≥80)</th>
                    <th className="py-4 px-3 text-right">Interesantes</th>
                    <th className="py-4 px-3 text-right">Score medio</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.byZone.map((row) => (
                    <tr key={row.zone} className="border-b border-slate-50 hover:bg-slate-50/50">
                      <td className="py-4 px-3 text-sm font-black text-slate-900">{row.zone}</td>
                      <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{row.count}</td>
                      <td className="py-4 px-3 text-right text-sm font-black text-[#00acee]">{formatPrice(row.avgPrice)}</td>
                      <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{formatPrice(row.medianPrice)}</td>
                      <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">
                        {row.avgM2Price ? `${fmtNum(row.avgM2Price)} €` : '—'}
                      </td>
                      <td className="py-4 px-3 text-right text-sm font-black text-orange-500">{row.hotCount}</td>
                      <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{row.warmCount}</td>
                      <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{fmtNum(row.avgScore, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="Tipo de vendedor" icon={<Users size={18} />}>
          <DonutLegend
            items={[
              { label: 'Particular', value: stats.sellerType.particular, color: '#10b981' },
              { label: 'Agencia', value: stats.sellerType.agency, color: '#6366f1' },
              { label: 'Sin datos', value: stats.sellerType.unknown, color: '#cbd5e1' },
            ]}
            total={stats.total}
          />
        </Panel>

        <Panel title="Oportunidad (score IA)" icon={<Flame size={18} />}>
          <DonutLegend
            items={[
              { label: 'TOP (≥80)', value: stats.opportunity.hot, color: '#f97316' },
              { label: 'Interesante (60–79)', value: stats.opportunity.warm, color: '#00acee' },
              { label: 'Normal (<60)', value: stats.opportunity.normal, color: '#94a3b8' },
            ]}
            total={stats.total}
          />
        </Panel>
      </div>

      {stats.bySource.length > 1 && (
        <Panel title="Tabla comparativa de fuentes" icon={<BarChart3 size={18} />} className="mb-12">
          <div className="overflow-x-auto -mx-2">
            <table className="w-full min-w-[640px] text-left">
              <thead>
                <tr className="text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100">
                  <th className="py-4 px-3">Fuente</th>
                  <th className="py-4 px-3 text-right">Anuncios</th>
                  <th className="py-4 px-3 text-right">Precio medio</th>
                  <th className="py-4 px-3 text-right">€/m² medio</th>
                  <th className="py-4 px-3 text-right">Score medio</th>
                  <th className="py-4 px-3 text-right">TOP</th>
                  <th className="py-4 px-3 text-right">% Particular</th>
                </tr>
              </thead>
              <tbody>
                {stats.bySource.map((row) => (
                  <tr key={row.source} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="py-4 px-3">
                      <span className="inline-flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: sourceColor(row.source) }} />
                        <span className="text-sm font-black text-slate-900">{row.source}</span>
                      </span>
                    </td>
                    <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{row.count}</td>
                    <td className="py-4 px-3 text-right text-sm font-black text-slate-800">{formatPrice(row.avgPrice)}</td>
                    <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">
                      {row.avgM2Price ? `${fmtNum(row.avgM2Price)} €/m²` : '—'}
                    </td>
                    <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{fmtNum(row.avgScore, 1)}</td>
                    <td className="py-4 px-3 text-right text-sm font-black text-orange-500">{row.hotCount}</td>
                    <td className="py-4 px-3 text-right text-sm font-bold text-slate-600">{fmtNum(row.particularPct, 0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        <Panel title="Mejor €/m² (top 5)" icon={<TrendingDown size={18} />}>
          {zoneOptions.length > 0 && (
            <div className="mb-6">
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">
                Zona
              </label>
              <select
                value={topDealsZone}
                onChange={(e) => setTopDealsZone(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-sm font-semibold text-slate-800 outline-none focus:border-[#00acee] focus:ring-2 focus:ring-[#00acee]/20"
              >
                <option value="">Todas las zonas</option>
                {zoneOptions.map((zone) => (
                  <option key={zone} value={zone}>{zone}</option>
                ))}
              </select>
            </div>
          )}
          {topDeals.length === 0 ? (
            <EmptyPanel text={topDealsZone ? 'Sin datos de m² en esta zona' : 'Sin datos de m² suficientes'} />
          ) : (
            <div className="space-y-3">
              {topDeals.map((p, i) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onPropertySelect?.(p)}
                  className="w-full flex items-start gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 text-left hover:bg-white hover:border-[#00acee]/40 hover:shadow-md transition-all cursor-pointer group"
                >
                  <span className="text-2xl font-black text-slate-200 group-hover:text-[#00acee]/30">#{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-black text-slate-900 line-clamp-2 group-hover:text-[#00acee]">{p.title || 'Sin título'}</p>
                    <p className="text-[10px] font-bold text-slate-400 uppercase mt-1">
                      {p.source} · {p.city || '—'} · {p.size_m2 ? `${p.size_m2} m²` : '—'}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-black text-emerald-600">{fmtNum(p.m2Price, 0)} €/m²</p>
                    <p className="text-xs font-bold text-slate-500">{formatPrice(p.price)}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Extras detectados" icon={<Home size={18} />}>
          <div className="grid grid-cols-3 gap-4">
            <FeatureBox label="Parking" count={stats.features.parking} total={stats.total} />
            <FeatureBox label="Terraza" count={stats.features.terrace} total={stats.total} />
            <FeatureBox label="Piscina" count={stats.features.pool} total={stats.total} />
          </div>
        </Panel>
      </div>
    </section>
  )
}

function SourceChip({ label, count, active, color, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border-2 ${
        active
          ? 'text-white shadow-lg'
          : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
      }`}
      style={active ? { backgroundColor: color, borderColor: color } : undefined}
    >
      {label}
      {count != null ? ` (${count})` : ''}
    </button>
  )
}

function KpiCard({ icon, label, value, sub, accent }) {
  return (
    <div className="p-6 rounded-[2rem] border border-slate-100 bg-slate-50/50 hover:bg-white hover:shadow-lg transition-all">
      <div className={`p-2.5 rounded-xl w-fit mb-4 ${accent === 'orange' ? 'bg-orange-100 text-orange-600' : 'bg-[#0f172a] text-white'}`}>
        {icon}
      </div>
      <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</p>
      <p className="text-2xl lg:text-3xl font-black text-slate-900 mt-1">{value}</p>
      {sub && <p className="text-[10px] font-bold text-slate-400 mt-2 uppercase tracking-wider">{sub}</p>}
    </div>
  )
}

function Panel({ title, icon, children, className = '' }) {
  return (
    <div className={`p-8 rounded-[2.5rem] border border-slate-100 bg-white shadow-sm ${className}`}>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-slate-100 text-slate-600">{icon}</div>
        <h3 className="text-sm font-black uppercase tracking-widest text-slate-900">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div>
      <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</p>
      <p className="text-lg font-black text-slate-900 mt-1">{value}</p>
    </div>
  )
}

function EmptyPanel({ text = 'Sin datos' }) {
  return <p className="text-sm text-slate-400 italic py-4">{text}</p>
}

function DonutLegend({ items, total }) {
  const safeTotal = total || 1
  return (
    <div className="space-y-4">
      {items.map((item) => {
        const pct = (item.value / safeTotal) * 100
        return (
          <div key={item.label}>
            <div className="flex justify-between mb-1.5">
              <span className="flex items-center gap-2 text-xs font-black text-slate-700">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                {item.label}
              </span>
              <span className="text-xs font-bold text-slate-400">
                {item.value} ({fmtNum(pct, 0)}%)
              </span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: item.color }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function FeatureBox({ label, count, total }) {
  const pct = total ? (count / total) * 100 : 0
  return (
    <div className="text-center p-4 rounded-2xl bg-slate-50 border border-slate-100">
      <p className="text-2xl font-black text-slate-900">{count}</p>
      <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mt-1">{label}</p>
      <p className="text-xs font-bold text-[#00acee] mt-2">{fmtNum(pct, 0)}%</p>
    </div>
  )
}
