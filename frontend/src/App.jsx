import { useState, useEffect } from 'react'
import { createClient } from '@insforge/sdk'
import { 
  Search, MapPin, Flame, User, LayoutDashboard, Filter, RefreshCw,
  Eye, Mail, MoreHorizontal, ChevronRight, ChevronLeft, Menu, X,
  ShieldCheck, AlertTriangle, Trash2, CheckCircle2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import PropertyIntelligenceModal from './PropertyIntelligenceModal'
import AdvisorChat from './AdvisorChat'
import SettingsView from './SettingsView'

const insforge = createClient({
  baseUrl: import.meta.env.VITE_INSFORGE_URL,
  anonKey: import.meta.env.VITE_INSFORGE_ANON_KEY
})

function App() {
  const [properties, setProperties] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [view, setView] = useState('dashboard')
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [errorField, setErrorField] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())

  const fetchProperties = async () => {
    setLoading(true)
    setErrorField(null)
    try {
      const { data, error } = await insforge.database
        .from('properties')
        .select('*')
        .order('created_at', { ascending: false })
      
      if (error) throw error
      if (data) setProperties(data)
    } catch (err) {
      console.error("Fetch error:", err)
      setErrorField("No se pudo conectar con la base de datos.")
    } finally {
      setLoading(false)
    }
  }

  const updateProperty = async (updatedProp) => {
    const { error } = await insforge.database
      .from('properties')
      .update(updatedProp)
      .match({ id: updatedProp.id })
    
    if (!error) {
      fetchProperties()
    }
  }

  const deleteProperty = async (id) => {
    const { error } = await insforge.database
      .from('properties')
      .delete()
      .match({ id })
    
    if (!error) {
      setSelectedIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      fetchProperties()
    }
  }

  const deleteBatch = async () => {
    if (!window.confirm(`¿Seguro que quieres eliminar ${selectedIds.size} propiedades?`)) return
    
    const idsToDelete = Array.from(selectedIds)
    const { error } = await insforge.database
      .from('properties')
      .delete()
      .in('id', idsToDelete)
    
    if (!error) {
      setSelectedIds(new Set())
      fetchProperties()
    }
  }

  const toggleSelect = (e, id) => {
    e.stopPropagation()
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleRefresh = async () => {
    setLoading(true)
    await fetchProperties()
    setLoading(false)
  }

  useEffect(() => {
    fetchProperties()
  }, [])

  const filteredProperties = properties.filter(p => {
    const s = searchTerm.toLowerCase()
    const matchesSearch = 
      (p.title || "").toLowerCase().includes(s) || 
      (p.city || "").toLowerCase().includes(s) ||
      (p.description || "").toLowerCase().includes(s)
    
    if (!matchesSearch) return false
    
    if (filter === 'hot') return p.opportunity_score >= 70
    if (filter === 'particular') return p.is_individual
    return true
  })

  const totalPages = Math.ceil(filteredProperties.length / itemsPerPage)
  const paginatedProperties = filteredProperties.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  return (
    <div className="flex min-h-screen bg-[#f8fafc] font-sans">
      <aside className="hidden lg:flex w-72 bg-[#0f172a] text-white flex-col fixed h-full z-50">
        <SidebarContent setView={setView} setFilter={setFilter} view={view} filter={filter} />
      </aside>

      <main className="flex-1 flex flex-col lg:ml-72 min-w-0 pb-24">
        <div className="relative h-[400px] bg-[#0f172a] flex flex-col justify-center px-12">
           <h1 className="text-5xl font-black text-white tracking-tighter">Gestión de <span className="text-[#00acee]">Activos.</span></h1>
           <p className="mt-4 text-slate-400 max-w-md font-medium">Control total sobre tu cartera de oportunidades detectadas por la IA.</p>
           
           <div className="mt-12 w-full max-w-2xl bg-white rounded-2xl p-2 flex items-center shadow-2xl">
              <Search className="ml-4 text-slate-300" />
              <input 
                type="text" 
                placeholder="Busca por zona o descripción..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1 py-4 px-4 outline-none font-bold text-slate-900"
              />
           </div>
        </div>

        <section className="p-12">
            <div className="flex justify-between items-center mb-12">
                <h2 className="text-2xl font-black text-slate-900 uppercase tracking-tight">Oportunidades</h2>
                <button onClick={handleRefresh} className="p-3 bg-white border border-slate-100 rounded-xl shadow-sm hover:bg-slate-50 transition-all text-slate-500">
                    <RefreshCw className={loading ? 'animate-spin' : ''} size={20} />
                </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-8">
                {paginatedProperties.map((prop) => (
                    <div 
                        key={prop.id} 
                        onClick={() => setSelectedProperty(prop)}
                        className={`group relative bg-white rounded-[2rem] overflow-hidden shadow-sm hover:shadow-xl transition-all border-2 cursor-pointer ${selectedIds.has(prop.id) ? 'border-[#00acee]' : 'border-transparent'}`}
                    >
                        {/* Checkbox Selector */}
                        <div 
                            onClick={(e) => toggleSelect(e, prop.id)}
                            className={`absolute top-4 left-4 z-20 w-8 h-8 rounded-full flex items-center justify-center transition-all ${selectedIds.has(prop.id) ? 'bg-[#00acee] text-white' : 'bg-black/20 text-white opacity-0 group-hover:opacity-100'}`}
                        >
                            {selectedIds.has(prop.id) ? <CheckCircle2 size={18} /> : <div className="w-4 h-4 border-2 border-white rounded-full" />}
                        </div>

                        <div className="aspect-[4/3] bg-slate-100">
                            <img src={prop.images?.[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000&auto=format&fit=crop'} className="w-full h-full object-cover" />
                        </div>
                        <div className="p-6">
                            <h3 className="font-bold text-slate-900 line-clamp-1">{prop.title}</h3>
                            <div className="flex justify-between items-center mt-3">
                                <span className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-1">
                                    <MapPin size={12} /> {prop.city}
                                </span>
                                <span className="text-sm font-black text-[#0f172a]">{prop.price?.toLocaleString()}€</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </section>

        {view === 'settings' && (
            <div className="fixed inset-0 z-[60] bg-[#f8fafc] overflow-y-auto">
                <button onClick={() => setView('dashboard')} className="fixed top-8 left-8 p-3 bg-white rounded-2xl shadow-xl z-[70]"><X /></button>
                <SettingsView insforge={insforge} />
            </div>
        )}

        {/* Bulk Action Bar */}
        <AnimatePresence>
            {selectedIds.size > 0 && (
                <motion.div 
                    initial={{ y: 100 }} animate={{ y: 0 }} exit={{ y: 100 }}
                    className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-[#0f172a] text-white px-8 py-4 rounded-3xl shadow-2xl flex items-center gap-8 z-[100]"
                >
                    <span className="text-sm font-black uppercase tracking-widest">{selectedIds.size} seleccionados</span>
                    <div className="h-8 w-px bg-white/10" />
                    <button onClick={deleteBatch} className="flex items-center gap-2 text-red-400 font-black uppercase text-xs hover:text-red-300 transition-colors">
                        <Trash2 size={16} /> Eliminar de la base de datos
                    </button>
                    <button onClick={() => setSelectedIds(new Set())} className="text-xs font-bold text-slate-400 hover:text-white transition-colors">Cancelar</button>
                </motion.div>
            )}
        </AnimatePresence>

        <AnimatePresence>
          {selectedProperty && (
            <PropertyIntelligenceModal 
                property={selectedProperty} 
                onClose={() => setSelectedProperty(null)} 
                onUpdate={updateProperty}
                onDelete={deleteProperty}
            />
          )}
        </AnimatePresence>
      </main>
      <AdvisorChat insforge={insforge} />
    </div>
  )
}

function SidebarContent({ setView, setFilter, view, filter }) {
    return (
        <div className="p-10 flex flex-col h-full">
            <h2 className="text-2xl font-black tracking-tighter text-white mb-12">HolanducIA.</h2>
            <nav className="space-y-4">
                <button onClick={() => {setView('dashboard'); setFilter('all')}} className={`w-full flex items-center gap-4 px-6 py-4 rounded-2xl font-bold uppercase text-xs tracking-widest transition-all ${view === 'dashboard' ? 'bg-[#00acee] text-white shadow-lg shadow-[#00acee40]' : 'text-slate-500 hover:bg-white/5'}`}>
                    <LayoutDashboard size={18} /> Dashboard
                </button>
                <button onClick={() => setView('settings')} className={`w-full flex items-center gap-4 px-6 py-4 rounded-2xl font-bold uppercase text-xs tracking-widest transition-all ${view === 'settings' ? 'bg-[#00acee] text-white shadow-lg shadow-[#00acee40]' : 'text-slate-500 hover:bg-white/5'}`}>
                    <Filter size={18} /> Configuración
                </button>
            </nav>
        </div>
    )
}

export default App
