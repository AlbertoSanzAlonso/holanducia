import { useState } from 'react'
import { ChevronLeft, ChevronRight, Images } from 'lucide-react'
import { resolveImageUrl } from './utils/propertyDisplay'

const FALLBACK =
  'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000&auto=format&fit=crop'

export function getPropertyImageUrls(images) {
  return (images || []).map(resolveImageUrl).filter(Boolean)
}

export default function PropertyGallery({ images = [], title = '', className = '', variant = 'full' }) {
  const urls = getPropertyImageUrls(images)
  const [index, setIndex] = useState(0)
  const compact = variant === 'card'

  if (!urls.length) {
    return (
      <div className={`relative bg-slate-100 ${className}`}>
        <img src={FALLBACK} alt={title} className="w-full h-full object-cover" />
      </div>
    )
  }

  const current = urls[Math.min(index, urls.length - 1)]
  const hasMultiple = urls.length > 1

  const prev = () => setIndex((i) => (i - 1 + urls.length) % urls.length)
  const next = () => setIndex((i) => (i + 1) % urls.length)

  return (
    <div className={`relative bg-slate-100 group ${className}`}>
      <img
        src={current}
        alt={title ? `${title} — foto ${index + 1}` : 'Propiedad'}
        className={`w-full h-full object-cover ${compact ? 'group-hover:scale-105 transition-transform duration-1000' : ''}`}
        onError={(e) => {
          e.currentTarget.src = FALLBACK
        }}
      />

      {hasMultiple && !compact && (
        <>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); prev() }}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-2.5 rounded-full bg-black/40 text-white opacity-0 group-hover:opacity-100 hover:bg-black/60 transition-all"
            aria-label="Foto anterior"
          >
            <ChevronLeft size={22} />
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); next() }}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-2.5 rounded-full bg-black/40 text-white opacity-0 group-hover:opacity-100 hover:bg-black/60 transition-all"
            aria-label="Foto siguiente"
          >
            <ChevronRight size={22} />
          </button>
          <div className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-black/50 text-white text-[10px] font-black uppercase tracking-widest">
            <Images size={12} />
            {index + 1}/{urls.length}
          </div>
          <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-1.5 px-4 overflow-x-auto">
            {urls.map((url, i) => (
              <button
                key={`${url}-${i}`}
                type="button"
                onClick={(e) => { e.stopPropagation(); setIndex(i) }}
                className={`shrink-0 w-12 h-12 rounded-lg overflow-hidden border-2 transition-all ${
                  i === index ? 'border-white scale-105' : 'border-white/30 opacity-70 hover:opacity-100'
                }`}
              >
                <img src={url} alt="" className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
