import { ArrowUpDown, Globe, MapPin, SlidersHorizontal, Tag, X } from 'lucide-react'
import { SORT_OPTIONS } from './utils/propertyFilters'

export default function PropertyFilters({
  filters,
  onChange,
  onReset,
  cities = [],
  sources = [],
  activeCount = 0,
  expanded,
  onToggleExpanded,
}) {
  const set = (key, value) => onChange({ ...filters, [key]: value })

  const toggleSource = (source) => {
    const current = filters.sources || []
    const next = current.includes(source)
      ? current.filter((s) => s !== source)
      : [...current, source]
    set('sources', next)
  }

  return (
    <div className="mb-12 rounded-[2rem] border border-slate-100 bg-slate-50/80 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={onToggleExpanded}
        className="w-full flex items-center justify-between gap-4 px-6 lg:px-8 py-5 hover:bg-white/60 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[#0f172a] text-white">
            <SlidersHorizontal size={18} />
          </div>
          <div className="text-left">
            <p className="text-sm font-black text-slate-900 uppercase tracking-widest">Buscador y filtros</p>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">
              {activeCount > 0 ? `${activeCount} filtro${activeCount > 1 ? 's' : ''} activo${activeCount > 1 ? 's' : ''}` : 'Precio, localidad, título y orden'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {activeCount > 0 && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onReset() }}
              className="hidden sm:flex items-center gap-1.5 px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-white hover:text-red-500 transition-colors"
            >
              <X size={14} /> Limpiar
            </button>
          )}
          <span className="text-[10px] font-black uppercase tracking-widest text-[#00acee]">
            {expanded ? 'Ocultar' : 'Mostrar'}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-6 lg:px-8 pb-8 pt-2 border-t border-slate-100/80 bg-white/50">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <FilterField label="Título / descripción" icon={<Tag size={14} />}>
              <input
                type="text"
                placeholder="Ej. ático, garaje, reformado..."
                value={filters.title}
                onChange={(e) => set('title', e.target.value)}
                className={inputClass}
              />
            </FilterField>

            <FilterField label="Localidad" icon={<MapPin size={14} />}>
              <select
                value={filters.city}
                onChange={(e) => set('city', e.target.value)}
                className={inputClass}
              >
                <option value="">Todas</option>
                {cities.map((city) => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </select>
            </FilterField>

            <FilterField label="Fuente" icon={<Globe size={14} />} className="sm:col-span-2 lg:col-span-2">
              <div className="flex flex-wrap gap-2 min-h-[46px] items-center">
                {sources.length === 0 ? (
                  <span className="text-xs text-slate-400 font-semibold px-1">Sin fuentes en la BD</span>
                ) : (
                  sources.map((source) => {
                    const active = (filters.sources || []).includes(source)
                    return (
                      <button
                        key={source}
                        type="button"
                        onClick={() => toggleSource(source)}
                        className={`px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all border-2 ${
                          active
                            ? 'bg-[#0f172a] text-white border-[#0f172a]'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-[#00acee]'
                        }`}
                      >
                        {source}
                      </button>
                    )
                  })
                )}
                {(filters.sources || []).length > 0 && (
                  <button
                    type="button"
                    onClick={() => set('sources', [])}
                    className="px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider text-slate-400 hover:text-red-500"
                  >
                    Todas
                  </button>
                )}
              </div>
            </FilterField>

            <FilterField label="Precio mín. (€)">
              <input
                type="number"
                min="0"
                step="1000"
                placeholder="0"
                value={filters.minPrice}
                onChange={(e) => set('minPrice', e.target.value)}
                className={inputClass}
              />
            </FilterField>

            <FilterField label="Precio máx. (€)">
              <input
                type="number"
                min="0"
                step="1000"
                placeholder="Sin límite"
                value={filters.maxPrice}
                onChange={(e) => set('maxPrice', e.target.value)}
                className={inputClass}
              />
            </FilterField>

            <FilterField label="Ordenar por" icon={<ArrowUpDown size={14} />} className="sm:col-span-2 lg:col-span-2">
              <select
                value={filters.sort}
                onChange={(e) => set('sort', e.target.value)}
                className={inputClass}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </FilterField>
          </div>

          {activeCount > 0 && (
            <button
              type="button"
              onClick={onReset}
              className="sm:hidden mt-4 w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-slate-200 text-[10px] font-black uppercase tracking-widest text-slate-500"
            >
              <X size={14} /> Limpiar filtros
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const inputClass =
  'w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-800 placeholder:text-slate-300 outline-none focus:border-[#00acee] focus:ring-2 focus:ring-[#00acee]/20 transition-all'

function FilterField({ label, icon, children, className = '' }) {
  return (
    <label className={`flex flex-col gap-2 ${className}`}>
      <span className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400">
        {icon}
        {label}
      </span>
      {children}
    </label>
  )
}
