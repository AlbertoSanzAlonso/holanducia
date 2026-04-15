import { useState, useEffect } from 'react'
import { createClient } from '@insforge/sdk'
import { 
  Search, 
  MapPin, 
  Flame, 
  User, 
  LayoutDashboard, 
  Filter,
  RefreshCw,
  Eye,
  Mail,
  MoreHorizontal,
  ChevronRight,
  ChevronLeft,
  Menu,
  X,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import PropertyIntelligenceModal from './PropertyIntelligenceModal'
import AdvisorChat from './AdvisorChat'
import SettingsView from './SettingsView'

// Initialize InsForge
const insforge = createClient({
  baseUrl: import.meta.env.VITE_INSFORGE_URL,
  anonKey: import.meta.env.VITE_INSFORGE_ANON_KEY
})

function App() {
  const [properties, setProperties] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [view, setView] = useState('dashboard') // 'dashboard' or 'settings'
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [errorField, setErrorField] = useState(null)

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

  const handleRefresh = async () => {
    setLoading(true)
    setErrorField(null)
    console.log("Refrescando datos locales...");
    await fetchProperties()
    setLoading(false)
  }

  useEffect(() => {
    fetchProperties()

    const setupRealtime = async () => {
      try {
        await insforge.realtime.connect()
        insforge.realtime.on('properties-changes', (event, payload) => {
          fetchProperties()
        })
        await insforge.realtime.subscribe('properties-changes')
      } catch (err) {
        // Reduciendo ruido en consola
      }
    }

    setupRealtime()

    return () => {
      insforge.realtime.disconnect()
    }
  }, [])

  const filteredProperties = properties.filter(p => {
    const s = searchTerm.toLowerCase()
    const matchesSearch = 
      (p.title || "").toLowerCase().includes(s) || 
      (p.city || "").toLowerCase().includes(s) ||
      (p.address || "").toLowerCase().includes(s) ||
      (p.neighborhood || "").toLowerCase().includes(s) ||
      (p.description || "").toLowerCase().includes(s)
    
    if (!matchesSearch) return false
    
    if (filter === 'hot') return p.opportunity_score >= 70
    if (filter === 'particular') return p.is_individual
    return true
  })

  // Pagination logic
  const totalPages = Math.ceil(filteredProperties.length / itemsPerPage)
  const paginatedProperties = filteredProperties.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  useEffect(() => {
    setCurrentPage(1) // Reset to page 1 when filter or search changes
  }, [filter, searchTerm])

  return (
    <div className="flex min-h-screen bg-[#f8fafc] font-sans selection:bg-[#00acee] selection:text-white">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex w-72 bg-[#0f172a] text-white flex-col fixed h-full shrink-0 shadow-2xl z-50">
        <SidebarContent 
          setView={setView} 
          setFilter={setFilter} 
          view={view} 
          filter={filter} 
        />
      </aside>

      {/* Sidebar - Mobile Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="fixed inset-0 bg-black/60 z-[60] lg:hidden backdrop-blur-sm"
            />
            <motion.aside 
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              className="fixed left-0 top-0 bottom-0 w-[280px] bg-[#0f172a] text-white z-[70] lg:hidden flex flex-col shadow-2xl"
            >
              <SidebarContent 
                setView={setView} 
                setFilter={setFilter} 
                view={view} 
                filter={filter} 
                onNavItemClick={() => setMobileMenuOpen(false)}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <main className="flex-1 flex flex-col lg:ml-72 min-w-0">
        {/* Hero Section */}
        <div className="relative min-h-[400px] lg:h-[500px] bg-[#0f172a] overflow-hidden flex flex-col justify-center px-6 lg:px-12 py-16">
          <div className="absolute inset-0 opacity-20 pointer-events-none">
            <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#00acee] blur-[120px] rounded-full" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#0072b1] blur-[100px] rounded-full" />
          </div>
          
          <div className="hidden lg:flex absolute top-0 left-0 w-full px-12 py-8 justify-between items-center text-white/50 text-xs font-bold tracking-widest uppercase">
             <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Detector de Subastas e Inteligencia en Tiempo Real
             </div>
             {errorField && (
               <div className="text-red-400 flex items-center gap-2 bg-red-400/10 px-4 py-2 rounded-xl animate-bounce">
                 <AlertTriangle size={14} /> {errorField}
               </div>
             )}
          </div>

          <div className="relative z-10 flex flex-col items-center lg:items-start text-center lg:text-left">
            <motion.h1 
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-4xl sm:text-6xl lg:text-7xl font-black text-white tracking-tighter leading-tight"
            >
              Analiza el <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00acee] to-[#60a5fa]">Mercado Vivo.</span>
            </motion.h1>
            <p className="mt-6 lg:mt-8 text-slate-400 max-w-xl text-base lg:text-lg font-medium leading-relaxed opacity-90">
              Usa los filtros de radar para limpiar el ruido. Buscaremos por ti solo las piezas que encajan con tu estrategia de inversión.
            </p>
          </div>

          {/* Floating Search */}
          <div className="mt-12 lg:mt-16 relative z-30 w-full max-w-3xl">
             <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-3xl p-2 lg:p-3 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.3)] border border-slate-100/50 flex flex-col sm:flex-row items-center gap-2"
             >
                <div className="hidden sm:flex pl-4 text-slate-400">
                   <Search size={22} />
                </div>
                <input 
                  type="text" 
                  placeholder="Busca barrios, calles o 'terraza', 'reforma'..." 
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full py-4 px-5 sm:px-2 text-slate-900 font-bold focus:outline-none text-base bg-transparent placeholder:text-slate-300"
                />
                <button 
                  onClick={() => setView('dashboard')}
                  className="w-full sm:w-auto bg-[#0f172a] text-white px-10 py-4 rounded-2xl font-black uppercase text-xs tracking-[0.1em] hover:bg-slate-800 transition-all active:scale-95 shadow-xl shadow-slate-900/10"
                >
                  Filtrar
                </button>
             </motion.div>
          </div>
        </div>

        {view === 'dashboard' ? (
          <section className="bg-white pt-12 lg:pt-16 pb-12 px-6 lg:px-12 min-h-screen">
             <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 lg:mb-12 border-b border-slate-100 pb-10 gap-6">
                <div>
                   <h2 className="text-slate-900 text-2xl lg:text-3xl font-black tracking-tight">Vigilante de Inversión</h2>
                   <p className="text-slate-400 text-sm mt-1.5 font-bold uppercase tracking-widest opacity-60">
                      Mostrando {paginatedProperties.length} de {filteredProperties.length} resultados (Pág. {currentPage} de {totalPages || 1})
                   </p>
                </div>
                <div className="flex items-center gap-3">
                   <button 
                    onClick={handleRefresh}
                    disabled={loading}
                    title="Actualizar vista con datos guardados"
                    className="flex items-center justify-center w-12 h-12 rounded-2xl shadow-lg transition-all disabled:opacity-50 bg-[#00acee] hover:bg-[#0072b1] text-white"
                   >
                     <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                   </button>
                   <div className="h-10 w-px bg-slate-100 mx-1" />
                   <div className="flex bg-slate-50 p-1.5 rounded-2xl border border-slate-100">
                      <button 
                        onClick={() => setFilter('all')}
                        className={`px-5 py-2 text-[10px] font-black rounded-xl uppercase tracking-widest transition-all ${filter === 'all' ? 'bg-[#0f172a] text-white shadow-xl shadow-slate-900/20' : 'text-slate-500 hover:text-slate-900'}`}
                      >
                        TODOS
                      </button>
                      <button 
                        onClick={() => setFilter('hot')}
                        className={`px-5 py-2 text-[10px] font-black rounded-xl uppercase tracking-widest transition-all ${filter === 'hot' ? 'bg-[#0f172a] text-white shadow-xl shadow-slate-900/20' : 'text-slate-500 hover:text-slate-900'}`}
                      >
                        TOP
                      </button>
                   </div>
                </div>
             </div>

             <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-8">
              <AnimatePresence mode="popLayout">
                {paginatedProperties.map((prop, idx) => {
                  const hasDiscrepancy = prop.opportunity_reasons?.some(r => r.includes("Discrepancia"));
                  const isVerified = !!prop.catastro_ref;

                  return (
                    <motion.div
                      key={prop.id}
                      layout
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      onClick={() => setSelectedProperty(prop)}
                      className="flex flex-col group cursor-pointer"
                    >
                      <div className="relative aspect-[4/3] rounded-3xl overflow-hidden bg-slate-100 shadow-sm mb-5">
                        <img 
                          src={prop.images?.[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000&auto=format&fit=crop'} 
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000"
                          alt={prop.title}
                        />
                        <div className="absolute inset-0 bg-[#0f172a]/60 opacity-0 group-hover:opacity-100 transition-all duration-300 flex flex-col items-center justify-center backdrop-blur-[2px]">
                           <div className="w-14 h-14 bg-white text-[#0f172a] rounded-full flex items-center justify-center shadow-2xl scale-75 group-hover:scale-100 transition-transform duration-300 mb-2">
                              <Eye size={24} />
                           </div>
                           <span className="text-white text-[10px] font-black uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">Ver Radiografía</span>
                        </div>
                        
                        <div className="absolute top-4 left-4 flex flex-col gap-2">
                           {isVerified && (
                             <div className="bg-green-500 text-white text-[9px] font-black px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-lg shadow-green-500/20">
                               <ShieldCheck size={12} /> CATASTRO OK
                             </div>
                           )}
                           {hasDiscrepancy && (
                             <div className="bg-orange-500 text-white text-[9px] font-black px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-lg shadow-orange-500/20">
                               <AlertTriangle size={12} /> ALERTA M2
                             </div>
                           )}
                        </div>

                        {prop.opportunity_score >= 80 && (
                          <div className="absolute top-4 right-4 bg-orange-500 text-white text-[10px] font-black px-4 py-1.5 rounded-full">TOP SCORE</div>
                        )}
                        <div className="absolute bottom-4 left-4 bg-[#0f172a]/40 backdrop-blur-md text-white text-[9px] font-black px-3 py-1.5 rounded-lg border border-white/10 uppercase tracking-widest">
                           {prop.source}
                        </div>
                      </div>
                      <div className="flex justify-between items-start gap-4 px-1">
                         <div className="flex-1">
                            <h3 className="text-slate-900 font-bold text-base leading-snug line-clamp-2">{prop.title}</h3>
                            <div className="flex items-center gap-4 mt-3">
                               <p className="text-slate-400 text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5">
                                 <MapPin size={12} className="text-[#00acee]" /> {prop.city}
                               </p>
                               {prop.size_m2 && (
                                 <p className="text-slate-400 text-[10px] font-black uppercase tracking-wider">
                                   {prop.size_m2} m²
                                 </p>
                               )}
                            </div>
                         </div>
                         <div className="text-lg font-black text-[#0f172a] bg-slate-50 px-3 py-1 rounded-lg">
                            {prop.price?.toLocaleString('es-ES')}€
                         </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
             </div>

             {/* Pagination Controls */}
             {totalPages > 1 && (
               <div className="mt-16 flex items-center justify-center gap-4">
                  <button 
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-white border border-slate-100 text-[#0f172a] font-bold text-sm shadow-sm disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-50 transition-all"
                  >
                    <ChevronLeft size={18} /> Anterior
                  </button>
                  <div className="flex items-center gap-2">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className={`w-10 h-10 rounded-xl font-bold text-xs transition-all ${currentPage === p ? 'bg-[#0f172a] text-white' : 'bg-white text-slate-400 border border-slate-100 hover:bg-slate-50'}`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                  <button 
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-[#0f172a] text-white font-bold text-sm shadow-xl shadow-slate-900/10 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-800 transition-all"
                  >
                    Siguiente <ChevronRight size={18} />
                  </button>
               </div>
             )}

             {filteredProperties.length === 0 && !loading && (
                <div className="py-32 flex flex-col items-center text-center">
                   <div className="w-24 h-24 bg-slate-50 rounded-3xl flex items-center justify-center mb-6 border border-slate-100 text-slate-200">
                      <Search size={32} />
                   </div>
                   <h3 className="text-slate-900 text-xl font-black uppercase tracking-tight">Sin resultados</h3>
                   <p className="text-slate-400 text-sm mt-2 max-w-xs font-medium italic">Intenta buscar por barrio o reduce el nivel de filtros.</p>
                </div>
             )}
          </section>
        ) : (
          <SettingsView insforge={insforge} />
        )}
      </main>

      <AnimatePresence>
        {selectedProperty && (
          <PropertyIntelligenceModal 
            property={selectedProperty} 
            onClose={() => setSelectedProperty(null)} 
          />
        )}
      </AnimatePresence>
      <AdvisorChat insforge={insforge} />
    </div>
  )
}

function SidebarContent({ setView, setFilter, view, filter, onNavItemClick }) {
  const handleClick = (v, f) => {
    setView(v)
    if (f) setFilter(f)
    if (onNavItemClick) onNavItemClick()
  }

  return (
    <div className="flex flex-col h-full bg-[#0f172a]">
      <div className="p-10 flex flex-col items-center border-b border-white/5">
        <div className="relative mb-8">
          <div className="w-20 h-20 bg-gradient-to-tr from-[#00acee] to-[#0072b1] rounded-[2.2rem] flex items-center justify-center shadow-2xl transform rotate-6 hover:rotate-0 transition-transform duration-500">
            <span className="text-3xl font-black text-white -rotate-6">H.</span>
          </div>
          <div className="absolute -bottom-2 -right-2 w-7 h-7 bg-green-500 rounded-full border-4 border-[#0f172a] shadow-lg" />
        </div>
        <h2 className="text-2xl font-black tracking-tight uppercase text-white">HolanducIA</h2>
        <p className="text-[#00acee] text-[10px] font-black mt-2 uppercase tracking-[0.3em] opacity-80">Real Estate Intelligence</p>
      </div>

      <nav className="flex-1 px-6 mt-12 space-y-3">
        <NavItem 
          active={view === 'dashboard' && filter === 'all'} 
          onClick={() => handleClick('dashboard', 'all')}
          icon={<LayoutDashboard size={20} />}
          label="Radar General"
        />
        <NavItem 
          active={view === 'dashboard' && filter === 'hot'} 
          onClick={() => handleClick('dashboard', 'hot')}
          icon={<Flame size={20} />}
          label="Hot Leads"
          badge="80+"
        />
        <NavItem 
          active={view === 'dashboard' && filter === 'particular'} 
          onClick={() => handleClick('dashboard', 'particular')}
          icon={<User size={20} />}
          label="Particulares"
        />
        
        <div className="py-10 px-4">
           <div className="h-px bg-white/5 w-full" />
        </div>

        <p className="px-5 text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Radar</p>
        
        <NavItem 
          active={view === 'settings'} 
          onClick={() => handleClick('settings')}
          icon={<Filter size={20} />}
          label="Zonas y Filtros"
        />
      </nav>

      <div className="p-10 mt-auto">
         <div className="bg-white/5 p-4 rounded-2xl border border-white/5 flex items-center justify-between text-slate-500">
            <span className="text-[10px] font-black tracking-widest uppercase">PRO v2.0.5</span>
            <MoreHorizontal size={20} className="cursor-pointer hover:text-white transition-colors" />
         </div>
      </div>
    </div>
  )
}

function NavItem({ active, onClick, icon, label, badge }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center justify-between px-5 py-4 rounded-[1.25rem] transition-all duration-300 group ${active ? 'bg-gradient-to-r from-[#00acee] to-[#0072b1] text-white shadow-2xl shadow-[#00acee40]' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
    >
      <div className="flex items-center gap-4">
        <span className={`${active ? 'text-white' : 'text-slate-500 group-hover:text-[#00acee]'} transition-colors`}>{icon}</span>
        <span className="text-sm font-black uppercase tracking-wider">{label}</span>
      </div>
      {badge && (
        <span className={`text-[9px] font-black px-2 py-0.5 rounded-md ${active ? 'bg-white/20 text-white' : 'bg-[#00acee]/10 text-[#00acee]'}`}>
          {badge}
        </span>
      )}
    </button>
  )
}

export default App
