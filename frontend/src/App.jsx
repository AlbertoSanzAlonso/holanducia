import { useState, useEffect } from 'react'
import { createClient } from '@insforge/sdk'
import { 
  Search, MapPin, Flame, User, LayoutDashboard, Filter, RefreshCw,
  Eye, Mail, MoreHorizontal, ChevronRight, ChevronLeft, Menu, X,
  ShieldCheck, AlertTriangle, Trash2, CheckCircle2, FolderHeart, Tag
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
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [selectedCategoryId, setSelectedCategoryId] = useState(null)
  const [view, setView] = useState('dashboard')
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())

  const fetchData = async () => {
    setLoading(true)
    const [propsRes, catsRes] = await Promise.all([
      insforge.database.from('properties').select('*').order('created_at', { ascending: false }),
      insforge.database.from('categories').select('*').order('name', { ascending: true })
    ])
    
    if (propsRes.data) setProperties(propsRes.data)
    if (catsRes.data) setCategories(catsRes.data)
    setLoading(false)
  }

  const updateProperty = async (updatedProp) => {
    const { error } = await insforge.database
      .from('properties')
      .update(updatedProp)
      .match({ id: updatedProp.id })
    if (!error) fetchData()
  }

  const deleteProperty = async (id) => {
    const { error } = await insforge.database.from('properties').delete().match({ id })
    if (!error) fetchData()
  }

  const deleteBatch = async () => {
    if (!window.confirm(`¿Eliminar ${selectedIds.size} elementos?`)) return
    await insforge.database.from('properties').delete().in('id', Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
  }

  const changeBatchCategory = async (catId) => {
    await insforge.database.from('properties').update({ category_id: catId }).in('id', Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
    alert('Cartera actualizada con éxito.')
  }

  useEffect(() => { fetchData() }, [])

  const filteredProperties = properties.filter(p => {
    const s = searchTerm.toLowerCase()
    const matchesSearch = (p.title || "").toLowerCase().includes(s) || (p.city || "").toLowerCase().includes(s)
    if (!matchesSearch) return false
    
    if (selectedCategoryId) return p.category_id === selectedCategoryId
    if (filter === 'hot') return p.opportunity_score >= 70
    if (filter === 'particular') return p.is_individual
    return true
  })

  return (
    <div className="flex min-h-screen bg-[#f8fafc] font-sans">
      <aside className="hidden lg:flex w-72 bg-[#0f172a] text-white flex-col fixed h-full z-50">
        <SidebarContent 
            setView={setView} 
            setFilter={setFilter} 
            setSelectedCategoryId={setSelectedCategoryId}
            categories={categories}
            view={view} 
            filter={filter} 
            selectedCategoryId={selectedCategoryId}
        />
      </aside>

      <main className="flex-1 flex flex-col lg:ml-72 min-w-0 pb-24">
        {/* Header Hero */}
        <div className="relative h-[300px] bg-[#0f172a] flex flex-col justify-center px-12">
           <h1 className="text-4xl font-black text-white uppercase tracking-tighter">Mi Cartera de <span className="text-[#00acee]">Inversión</span></h1>
           <div className="mt-8 w-full max-w-xl bg-white/10 backdrop-blur-md rounded-2xl p-2 flex items-center border border-white/5">
              <Search className="ml-4 text-white/30" />
              <input 
                type="text" 
                placeholder="Filtrar por zona..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="flex-1 py-3 px-4 bg-transparent outline-none font-bold text-white placeholder:text-white/20"
              />
           </div>
        </div>

        <section className="p-12">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-8">
                {filteredProperties.map((prop) => (
                    <div 
                        key={prop.id} 
                        onClick={() => setSelectedProperty(prop)}
                        className={`group relative bg-white rounded-[2rem] overflow-hidden shadow-sm hover:shadow-xl transition-all border-2 ${selectedIds.has(prop.id) ? 'border-[#00acee]' : 'border-transparent'}`}
                    >
                        <div 
                            onClick={(e) => { e.stopPropagation(); setSelectedIds(prev => { const n = new Set(prev); if(n.has(prop.id)) n.delete(prop.id); else n.add(prop.id); return n; })}}
                            className={`absolute top-4 left-4 z-20 w-8 h-8 rounded-full flex items-center justify-center transition-all ${selectedIds.has(prop.id) ? 'bg-[#00acee] text-white' : 'bg-black/20 text-white opacity-0 group-hover:opacity-100'}`}
                        >
                            {selectedIds.has(prop.id) ? <CheckCircle2 size={18} /> : <div className="w-4 h-4 border-2 border-white rounded-full" />}
                        </div>
                        <div className="aspect-[4/3] bg-slate-100">
                            <img src={prop.images?.[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000' } className="w-full h-full object-cover" />
                        </div>
                        <div className="p-6">
                            <div className="flex gap-2 mb-2">
                                {categories.find(c => c.id === prop.category_id) && (
                                    <span style={{ backgroundColor: categories.find(c => c.id === prop.category_id).color }} className="px-2 py-0.5 rounded text-[8px] font-black text-white uppercase">
                                        {categories.find(c => c.id === prop.category_id).name}
                                    </span>
                                )}
                            </div>
                            <h3 className="font-bold text-slate-900 text-sm line-clamp-1">{prop.title}</h3>
                            <div className="flex justify-between items-center mt-3">
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{prop.city}</span>
                                <span className="text-sm font-black text-[#0f172a]">{prop.price?.toLocaleString()}€</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </section>

        {/* Bulk Bar with Categories */}
        <AnimatePresence>
            {selectedIds.size > 0 && (
                <motion.div 
                    initial={{ y: 100 }} animate={{ y: 0 }} exit={{ y: 100 }}
                    className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-[#0f172a] text-white px-8 py-5 rounded-[2.5rem] shadow-2xl flex items-center gap-6 z-[100] border border-white/10"
                >
                    <span className="text-xs font-black uppercase text-[#00acee]">{selectedIds.size} Marcados</span>
                    <div className="h-6 w-px bg-white/10" />
                    <div className="flex items-center gap-2 overflow-x-auto max-w-sm no-scrollbar">
                        {categories.map(cat => (
                            <button 
                                key={cat.id} 
                                onClick={() => changeBatchCategory(cat.id)}
                                className="whitespace-nowrap px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/10 text-[9px] font-bold transition-all"
                            >
                                Mover a {cat.name}
                            </button>
                        ))}
                    </div>
                    <div className="h-6 w-px bg-white/10" />
                    <button onClick={deleteBatch} className="text-red-400 p-2 hover:bg-red-400/10 rounded-lg"><Trash2 size={18} /></button>
                </motion.div>
            )}
        </AnimatePresence>

        {view === 'settings' && (
            <div className="fixed inset-0 z-[120] bg-white"><SettingsView insforge={insforge} /></div>
        )}

        <AnimatePresence>
          {selectedProperty && (
            <PropertyIntelligenceModal 
                property={selectedProperty} 
                categories={categories}
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

function SidebarContent({ setView, setFilter, setSelectedCategoryId, categories, view, filter, selectedCategoryId }) {
    return (
        <div className="p-8 flex flex-col h-full bg-[#0f172a]">
            <h2 className="text-2xl font-black text-white tracking-tighter mb-12">HolanducIA</h2>
            
            <nav className="space-y-2">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Radar General</p>
                <button onClick={() => {setView('dashboard'); setFilter('all'); setSelectedCategoryId(null)}} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold uppercase text-[10px] tracking-widest ${view === 'dashboard' && !selectedCategoryId && filter === 'all' ? 'bg-[#00acee] text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}>
                    <LayoutDashboard size={16} /> Todo el mercado
                </button>
                <button onClick={() => setView('settings')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold uppercase text-[10px] tracking-widest ${view === 'settings' ? 'bg-[#00acee] text-white' : 'text-slate-400'}`}>
                    <Filter size={16} /> Configuración
                </button>
            </nav>

            <nav className="mt-12 space-y-2">
                <div className="flex items-center justify-between mb-4">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Mi Cartera</p>
                    <FolderHeart size={14} className="text-[#00acee]" />
                </div>
                {categories.map(cat => (
                    <button 
                        key={cat.id} 
                        onClick={() => {setView('dashboard'); setSelectedCategoryId(cat.id)}}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold uppercase text-[10px] tracking-widest transition-all ${selectedCategoryId === cat.id ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-slate-300'}`}
                    >
                        <Tag size={14} style={{ color: cat.color }} /> {cat.name}
                    </button>
                ))}
            </nav>
        </div>
    )
}

export default App
