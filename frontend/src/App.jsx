import { useState, useEffect } from 'react'
import { createClient } from '@insforge/sdk'
import { 
  Search, MapPin, Flame, User, LayoutDashboard, Filter, RefreshCw,
  Eye, Mail, MoreHorizontal, ChevronRight, ChevronLeft, Menu, X,
  ShieldCheck, AlertTriangle, Trash2, CheckCircle2, FolderHeart, Tag,
  BarChart3, Settings as SettingsIcon, LayoutGrid
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
  const [errorField, setErrorField] = useState(null)
  const [securityBlock, setSecurityBlock] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
        const [propsRes, catsRes] = await Promise.all([
        insforge.database.from('properties').select('*').order('created_at', { ascending: false }),
        insforge.database.from('categories').select('*').order('name', { ascending: true })
        ])
        if (propsRes.data) setProperties(propsRes.data)
        if (catsRes.data) setCategories(catsRes.data)
    } catch (e) {
        setErrorField("Revisa la conexión con el servidor.")
    } finally {
        setLoading(false)
    }
  }

  const updateProperty = async (updatedProp) => {
    const { error } = await insforge.database.from('properties').update(updatedProp).match({ id: updatedProp.id })
    if (!error) fetchData()
  }

  const deleteProperty = async (id) => {
    const { error } = await insforge.database.from('properties').delete().match({ id })
    if (!error) { 
        setSelectedIds(prev => { const n = new Set(prev); n.delete(id); return n; })
        fetchData() 
    }
  }

  const deleteBatch = async () => {
    if (!window.confirm(`¿Seguro que quieres eliminar ${selectedIds.size} elementos?`)) return
    await insforge.database.from('properties').delete().in('id', Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
  }

  const changeBatchCategory = async (catId) => {
    await insforge.database.from('properties').update({ category_id: catId }).in('id', Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
  }

  const checkScrapingStatus = async () => {
    const { data } = await insforge.database
      .from('scraping_requests')
      .select('*')
      .order('requested_at', { ascending: false })
      .limit(1)
    
    if (data?.[0]?.status === 'security_block') {
      setSecurityBlock(data[0])
    } else {
      setSecurityBlock(null)
    }
  }

  useEffect(() => { 
    fetchData()
    const interval = setInterval(checkScrapingStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const filteredProperties = properties.filter(p => {
    const s = searchTerm.toLowerCase()
    const matchesSearch = (p.title || "").toLowerCase().includes(s) || (p.city || "").toLowerCase().includes(s)
    if (!matchesSearch) return false
    if (selectedCategoryId) return p.category_id === selectedCategoryId
    if (filter === 'hot') return p.opportunity_score >= 80
    if (filter === 'particular') return p.is_individual
    return true
  })

  const paginatedProperties = filteredProperties.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  return (
    <div className="flex min-h-screen bg-[#f8fafc] font-sans selection:bg-[#00acee] selection:text-white">
      {/* Sidebar Premium */}
      <aside className="hidden lg:flex w-80 bg-[#0f172a] text-white flex-col fixed h-full z-50 shadow-2xl">
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

      <main className="flex-1 flex flex-col lg:ml-80 min-w-0">
        {/* Cinema Hero Section */}
        <div className="relative min-h-[500px] bg-[#0f172a] overflow-hidden flex flex-col justify-center px-6 lg:px-16 py-24">
          <div className="absolute inset-0 opacity-30 pointer-events-none">
            <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-[#00acee] blur-[150px] rounded-full" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[#4f46e5] blur-[130px] rounded-full" />
          </div>
          
          <div className="relative z-10">
            <motion.span 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="inline-block text-[#00acee] text-xs font-black tracking-[0.4em] uppercase mb-6"
            >
              Intelligence Platform v2.0
            </motion.span>
            <motion.h1 
              initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
              className="text-5xl sm:text-7xl lg:text-8xl font-black text-white tracking-tighter leading-[0.9]"
            >
              Analiza el <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00acee] to-[#818cf8]">Mercado Vivo.</span>
            </motion.h1>
            
            <div className="mt-16 w-full max-w-3xl">
               <div className="bg-white/10 backdrop-blur-2xl rounded-[2.5rem] p-3 shadow-2xl border border-white/10 flex flex-col sm:flex-row items-center gap-2">
                  <div className="hidden sm:flex pl-6 text-white/30"><Search size={28} /></div>
                  <input 
                    type="text" 
                    placeholder="Busca barrios, calles o descripción..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full py-5 px-6 sm:px-4 bg-transparent outline-none text-xl font-bold text-white placeholder:text-white/20"
                  />
                  <button className="w-full sm:w-auto bg-[#00acee] text-white px-10 py-5 rounded-[1.8rem] font-black uppercase text-xs tracking-widest hover:bg-[#009bd6] transition-all active:scale-95 shadow-xl shadow-[#00acee/20]">
                    Buscar
                  </button>
               </div>
            </div>
          </div>
        </div>

        {/* Security Block Alert */}
        <AnimatePresence>
          {securityBlock && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
              className="bg-orange-600 text-white px-6 lg:px-16 overflow-hidden shadow-2xl z-40"
            >
              <div className="py-6 flex flex-col sm:flex-row items-center justify-between gap-6 border-b border-white/10">
                <div className="flex items-center gap-6">
                  <div className="p-4 bg-white/20 rounded-2xl animate-pulse">
                    <AlertTriangle size={32} />
                  </div>
                  <div>
                    <h4 className="text-xl font-black uppercase tracking-tight">Acción Requerida: Bloqueo de Facebook</h4>
                    <p className="text-white/80 font-bold text-sm">El robot necesita que confirmes el inicio de sesión para continuar.</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <a 
                    href="https://www.facebook.com" target="_blank" rel="noreferrer"
                    className="bg-white text-orange-600 px-8 py-4 rounded-2xl font-black uppercase text-xs tracking-widest hover:bg-orange-50 transition-all active:scale-95"
                  >
                    Confirmar en Facebook
                  </a>
                  <button 
                    onClick={() => setSecurityBlock(null)}
                    className="p-4 text-white hover:bg-white/10 rounded-2xl transition-all"
                  >
                    <X size={24} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {view === 'dashboard' ? (
          <section className="bg-white p-6 lg:p-16 min-h-screen">
             <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-16 gap-8">
                <div>
                   <h2 className="text-4xl lg:text-5xl font-black text-slate-900 tracking-tight">Vigilante de Inversión</h2>
                   <p className="text-slate-400 text-sm mt-3 font-bold uppercase tracking-[0.2em]">{filteredProperties.length} oportunidades encontradas</p>
                </div>
                <div className="flex items-center gap-4">
                   <button onClick={fetchData} className="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-slate-400 hover:bg-white hover:shadow-xl transition-all">
                      <RefreshCw size={24} className={loading ? 'animate-spin' : ''} />
                   </button>
                   <div className="flex bg-slate-50 p-2 rounded-2xl border border-slate-100">
                      <button onClick={() => setFilter('all')} className={`px-6 py-2.5 text-[10px] font-black rounded-xl uppercase tracking-widest transition-all ${filter === 'all' ? 'bg-[#0f172a] text-white shadow-xl' : 'text-slate-500'}`}>TODOS</button>
                      <button onClick={() => setFilter('hot')} className={`px-6 py-2.5 text-[10px] font-black rounded-xl uppercase tracking-widest transition-all ${filter === 'hot' ? 'bg-[#0f172a] text-white shadow-xl' : 'text-slate-500'}`}>TOP</button>
                   </div>
                </div>
             </div>

             <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-12">
                {paginatedProperties.map((prop, idx) => (
                    <motion.div 
                        key={prop.id}
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                        onClick={() => setSelectedProperty(prop)}
                        className={`group relative flex flex-col cursor-pointer ${selectedIds.has(prop.id) ? 'scale-[0.98]' : ''}`}
                    >
                        <div className={`relative aspect-[4/3] rounded-[2.5rem] overflow-hidden bg-slate-100 shadow-lg mb-6 border-4 transition-all ${selectedIds.has(prop.id) ? 'border-[#00acee]' : 'border-transparent'}`}>
                          <img src={prop.images?.[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000' } className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000" />
                          <div className="absolute inset-0 bg-[#0f172a]/60 opacity-0 group-hover:opacity-100 transition-all flex items-center justify-center backdrop-blur-sm">
                             <div className="w-16 h-16 bg-white text-[#0f172a] rounded-full flex items-center justify-center shadow-2xl scale-75 group-hover:scale-100 transition-transform">
                                <Eye size={32} />
                             </div>
                          </div>
                          
                          {/* Selection Checkbox */}
                          <button 
                            onClick={(e) => {e.stopPropagation(); setSelectedIds(prev => {const n = new Set(prev); if(n.has(prop.id)) n.delete(prop.id); else n.add(prop.id); return n;})}}
                            className={`absolute top-6 left-6 w-10 h-10 rounded-2xl flex items-center justify-center transition-all shadow-xl ${selectedIds.has(prop.id) ? 'bg-[#00acee] text-white' : 'bg-black/20 text-white opacity-0 group-hover:opacity-100'}`}
                          >
                             {selectedIds.has(prop.id) ? <CheckCircle2 size={24} /> : <div className="w-5 h-5 border-2 border-white rounded-lg" />}
                          </button>

                          {prop.opportunity_score >= 80 && (
                            <div className="absolute top-6 right-6 bg-orange-500 text-white text-[10px] font-black px-5 py-2 rounded-full shadow-lg">TOP OPPORTUNITY</div>
                          )}
                          
                          <div className="absolute bottom-6 left-6 flex gap-2">
                             <div className="bg-[#0f172a]/40 backdrop-blur-md text-white text-[9px] font-black px-4 py-2 rounded-xl border border-white/10 uppercase tracking-widest">{prop.source}</div>
                             {categories.find(c => c.id === prop.category_id) && (
                                <div style={{backgroundColor: categories.find(c => c.id === prop.category_id).color}} className="text-white text-[9px] font-black px-4 py-2 rounded-xl uppercase tracking-widest shadow-lg">
                                    {categories.find(c => c.id === prop.category_id).name}
                                </div>
                             )}
                          </div>
                        </div>

                        <div className="px-2">
                           <h3 className="text-xl font-black text-slate-900 leading-tight mb-4 group-hover:text-[#00acee] transition-colors line-clamp-2">{prop.title}</h3>
                           <div className="flex justify-between items-center">
                              <div className="flex items-center gap-4 text-slate-400 text-[10px] font-black uppercase tracking-widest">
                                 <span className="flex items-center gap-1.5"><MapPin size={14} className="text-[#00acee]" /> {prop.city}</span>
                                 <span>{prop.size_m2} m²</span>
                              </div>
                              <div className="text-2xl font-black text-slate-900 bg-slate-50 px-4 py-2 rounded-2xl">{prop.price?.toLocaleString()}€</div>
                           </div>
                        </div>
                    </motion.div>
                ))}
             </div>

             {/* Paginación Nativa Premium - Ahora Centrada */}
             {filteredProperties.length > itemsPerPage && (
                <div className="mt-24 border-t border-slate-100 pt-12 flex flex-col items-center gap-8">
                    <div className="flex items-center gap-4">
                        <button 
                            disabled={currentPage === 1}
                            onClick={() => { setCurrentPage(p => p - 1); window.scrollTo({top: 400, behavior: 'smooth'}); }}
                            className="p-4 bg-white border border-slate-100 rounded-3xl text-slate-900 disabled:opacity-20 hover:shadow-2xl hover:scale-105 active:scale-95 transition-all shadow-xl shadow-slate-200/50"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <div className="flex gap-3">
                            {[...Array(Math.ceil(filteredProperties.length / itemsPerPage))].map((_, i) => (
                                <button 
                                    key={i}
                                    onClick={() => { setCurrentPage(i + 1); window.scrollTo({top: 400, behavior: 'smooth'}); }}
                                    className={`w-14 h-14 rounded-2xl font-black text-sm transition-all shadow-xl ${currentPage === i + 1 ? 'bg-slate-900 text-white shadow-slate-400/30' : 'bg-white border border-slate-50 text-slate-400 hover:border-slate-300'}`}
                                >
                                    {i + 1}
                                </button>
                            )).slice(Math.max(0, currentPage - 3), Math.min(Math.ceil(filteredProperties.length / itemsPerPage), currentPage + 2))}
                        </div>
                        <button 
                            disabled={currentPage >= Math.ceil(filteredProperties.length / itemsPerPage)}
                            onClick={() => { setCurrentPage(p => p + 1); window.scrollTo({top: 400, behavior: 'smooth'}); }}
                            className="p-4 bg-white border border-slate-100 rounded-3xl text-slate-900 disabled:opacity-20 hover:shadow-2xl hover:scale-105 active:scale-95 transition-all shadow-xl shadow-slate-200/50"
                        >
                            <ChevronRight size={24} />
                        </button>
                    </div>
                    <div className="text-slate-400 text-[10px] font-black uppercase tracking-[0.3em] bg-slate-50 px-6 py-2 rounded-full">
                        Visualizando página {currentPage} de {Math.ceil(filteredProperties.length / itemsPerPage)}
                    </div>
                </div>
             )}
          </section>
        ) : (
          <SettingsView insforge={insforge} />
        )}

        {/* Floating Bulk Actions Bar Premium */}
        <AnimatePresence>
            {selectedIds.size > 0 && (
                <motion.div 
                    initial={{ y: 120 }} animate={{ y: 0 }} exit={{ y: 120 }}
                    className="fixed bottom-12 left-1/2 -translate-x-1/2 bg-[#0f172a] text-white px-10 py-6 rounded-[3rem] shadow-[0_40px_100px_rgba(0,0,0,0.5)] flex items-center gap-10 z-[100] border border-white/10 backdrop-blur-3xl"
                >
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black text-[#00acee] uppercase tracking-[0.3em]">Acción Masiva</span>
                        <span className="text-lg font-black">{selectedIds.size} Elementos</span>
                    </div>
                    <div className="h-12 w-px bg-white/10" />
                    <div className="flex gap-3 overflow-x-auto max-w-[400px] no-scroll-bar">
                        {categories.map(cat => (
                            <button 
                                key={cat.id} onClick={() => changeBatchCategory(cat.id)}
                                className="whitespace-nowrap px-5 py-3 rounded-2xl border border-white/5 hover:bg-white/10 text-[10px] font-black uppercase tracking-widest transition-all"
                            >
                                {cat.name}
                            </button>
                        ))}
                    </div>
                    <div className="h-12 w-px bg-white/10" />
                    <button onClick={deleteBatch} className="p-4 bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white rounded-2xl transition-all"><Trash2 size={24} /></button>
                </motion.div>
            )}
        </AnimatePresence>

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
  const handleClick = (v, f, catId) => {
    setView(v)
    if (f !== undefined) setFilter(f)
    if (catId !== undefined) setSelectedCategoryId(catId)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-12 flex flex-col items-center">
        <div className="relative mb-8 group">
          <div className="w-24 h-24 bg-gradient-to-tr from-[#00acee] to-[#4f46e5] rounded-[2.5rem] flex items-center justify-center shadow-2xl transform rotate-6 group-hover:rotate-0 transition-transform duration-700">
            <span className="text-4xl font-black text-white -rotate-6 group-hover:rotate-0 transition-transform">H.</span>
          </div>
          <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-green-500 rounded-full border-4 border-[#0f172a] shadow-lg animate-pulse" />
        </div>
        <h2 className="text-3xl font-black tracking-tight text-white">HolanducIA.</h2>
        <p className="text-[#00acee] text-[9px] font-black mt-3 uppercase tracking-[0.4em] opacity-60">Real Estate Intelligence</p>
      </div>

      <nav className="flex-1 px-8 mt-12 space-y-3">
        <p className="px-6 text-[10px] font-black text-white/20 uppercase tracking-[0.3em] mb-4">Radar Principal</p>
        <SidebarNavItem active={view === 'dashboard' && !selectedCategoryId} icon={<LayoutGrid size={22} />} label="Todo el Mercado" onClick={() => handleClick('dashboard', 'all', null)} />
        <SidebarNavItem active={view === 'settings'} icon={<SettingsIcon size={22} />} label="Configuración" onClick={() => handleClick('settings')} />
        
        <div className="py-10 px-6"><div className="h-px bg-white/5 w-full" /></div>

        <p className="px-6 text-[10px] font-black text-white/20 uppercase tracking-[0.3em] mb-4">Mi Cartera</p>
        <div className="space-y-2">
            {categories.map(cat => (
                <SidebarNavItem 
                    key={cat.id}
                    active={selectedCategoryId === cat.id} 
                    icon={<Tag size={20} style={{ color: cat.color }} />} 
                    label={cat.name} 
                    onClick={() => handleClick('dashboard', 'all', cat.id)} 
                />
            ))}
        </div>
      </nav>

      <div className="p-12 mt-auto">
         <div className="bg-white/5 p-6 rounded-3xl border border-white/5 text-center">
            <span className="text-[10px] font-black text-white/30 tracking-[0.2em] uppercase">Enterprise Edition v2</span>
         </div>
      </div>
    </div>
  )
}

function SidebarNavItem({ active, icon, label, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-5 px-6 py-4 rounded-2xl transition-all duration-500 ${active ? 'bg-gradient-to-r from-[#00acee] to-[#4f46e5] text-white shadow-2xl shadow-[#00acee/40]' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
    >
      <span className={active ? 'text-white' : 'text-white/20'}>{icon}</span>
      <span className="text-xs font-black uppercase tracking-widest">{label}</span>
    </button>
  )
}

export default App
