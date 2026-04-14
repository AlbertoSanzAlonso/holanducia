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
  ChevronLeft
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// Initialize InsForge
const insforge = createClient({
  baseUrl: import.meta.env.VITE_INSFORGE_URL,
  anonKey: import.meta.env.VITE_INSFORGE_ANON_KEY
})

import SettingsView from './SettingsView'

function App() {
  const [properties, setProperties] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [view, setView] = useState('dashboard') // 'dashboard' or 'settings'
  const [searchTerm, setSearchTerm] = useState('')

  const fetchProperties = async () => {
    setLoading(true)
    const { data, error } = await insforge.database
      .from('properties')
      .select('*')
      .order('created_at', { ascending: false })
    
    if (data) setProperties(data)
    setLoading(false)
  }

  useEffect(() => {
    fetchProperties()

    const setupRealtime = async () => {
      try {
        await insforge.realtime.connect()
        insforge.realtime.on('properties-changes', (event, payload) => {
          console.log('Real-time update:', event, payload)
          fetchProperties()
        })
        await insforge.realtime.subscribe('properties-changes')
      } catch (err) {
        console.error('Real-time connection failed:', err)
      }
    }

    setupRealtime()

    return () => {
      insforge.realtime.disconnect()
    }
  }, [])

  const filteredProperties = properties.filter(p => {
    const matchesSearch = p.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                         p.city.toLowerCase().includes(searchTerm.toLowerCase())
    if (!matchesSearch) return false
    
    if (filter === 'hot') return p.opportunity_score >= 80
    if (filter === 'particular') return p.is_individual
    return true
  })

  return (
    <div className="flex min-h-screen bg-[#f3f4f6]">
      {/* Sidebar - HolanducIA Style */}
      <aside className="w-72 bg-[#0f172a] text-white flex flex-col fixed h-full shrink-0 shadow-2xl">
        <div className="p-8 flex flex-col items-center border-b border-white/5">
          <div className="relative mb-6">
            <div className="w-20 h-20 bg-gradient-to-tr from-[#00acee] to-[#0072b1] rounded-2xl flex items-center justify-center shadow-lg transform rotate-3">
              <span className="text-3xl font-black text-white -rotate-3">H.</span>
            </div>
            <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-green-500 rounded-full border-4 border-[#0f172a]" />
          </div>
          <h2 className="text-xl font-black tracking-tight uppercase">HolanducIA</h2>
          <p className="text-[#00acee] text-[10px] font-bold mt-1 uppercase tracking-[0.2em]">Real Estate AI</p>
          <div className="border-t border-white/5 w-full my-6" />
        </div>

        <nav className="flex-1 px-4 mt-2">
          <button 
            onClick={() => { setView('dashboard'); setFilter('all'); }}
            className={`w-full sidebar-link ${view === 'dashboard' && filter === 'all' ? 'active' : ''}`}
          >
            <LayoutDashboard size={18} /> Radar General
          </button>
          <button 
            onClick={() => { setView('dashboard'); setFilter('hot'); }}
            className={`w-full sidebar-link ${view === 'dashboard' && filter === 'hot' ? 'active' : ''}`}
          >
            <Flame size={18} className="text-orange-500" /> Hot Leads
          </button>
          <button 
            onClick={() => { setView('dashboard'); setFilter('particular'); }}
            className={`w-full sidebar-link ${view === 'dashboard' && filter === 'particular' ? 'active' : ''}`}
          >
            <User size={18} /> Particulares
          </button>
          
          <div className="my-6 mx-4 border-t border-white/5" />
          <p className="px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Ajustes</p>
          
          <button 
            onClick={() => setView('settings')}
            className={`w-full sidebar-link ${view === 'settings' ? 'active' : ''}`}
          >
            <RefreshCw size={18} /> Filtros de Búsqueda
          </button>
        </nav>

        <div className="p-8 mt-auto flex justify-between items-center text-slate-500 border-t border-white/5">
           <span className="text-[10px] font-medium tracking-widest">v1.2.4 PRO</span>
           <MoreHorizontal className="cursor-pointer hover:text-white transition-colors" />
        </div>
      </aside>

      {/* Content Area */}
      <main className="ml-72 flex-1 flex flex-col bg-[#f8fafc]">
        {/* Top Header - Premium Style */}
        <div className="relative h-[450px] bg-[#0f172a] overflow-hidden">
          {/* Abstract background pattern */}
          <div className="absolute inset-0 opacity-20 pointer-events-none">
            <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#00acee] blur-[120px] rounded-full" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#0072b1] blur-[100px] rounded-full" />
          </div>
          
          <div className="relative z-10 w-full px-12 py-8 flex justify-between items-center text-white/50 text-xs font-bold tracking-widest uppercase">
             <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Sistema de Análisis Activo
             </div>
             <div className="flex items-center gap-6">
                <span className="hover:text-white transition-colors cursor-pointer">Documentación</span>
                <span className="hover:text-white transition-colors cursor-pointer text-white">Alberto Alonso</span>
             </div>
          </div>

          <div className="relative z-10 flex flex-col items-center justify-center h-full -mt-16 px-6 text-center">
            <motion.h1 
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-6xl font-black text-white tracking-tighter sm:text-7xl"
            >
              Cazador de <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00acee] to-[#60a5fa]">Oportunidades.</span>
            </motion.h1>
            <p className="mt-8 text-slate-400 max-w-xl text-lg font-medium leading-relaxed">
              Analizamos miles de anuncios de portales inmobiliarios en tiempo real para encontrar los pisos con mayor potencial de rentabilidad.
            </p>
          </div>

          {/* Floating Search in Header */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 z-20 w-full max-w-2xl px-6">
             <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-2xl p-2 shadow-[0_20px_50px_rgba(0,0,0,0.15)] border border-slate-100 flex flex-col sm:flex-row items-center gap-2 sm:gap-4"
             >
                <div className="hidden sm:flex pl-4 text-slate-400">
                   <Search size={20} />
                </div>
                <input 
                  type="text" 
                  placeholder="Busca por zona, calle o portal..." 
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full py-4 px-4 sm:px-0 text-slate-900 font-medium focus:outline-none text-sm sm:text-base"
                />
                <button 
                  onClick={() => setView('dashboard')}
                  className="w-full sm:w-auto bg-[#0f172a] text-white px-8 py-4 rounded-xl font-bold hover:bg-slate-800 transition-all active:scale-95 shadow-lg shadow-slate-900/20"
                >
                  Buscar
                </button>
             </motion.div>
          </div>
        </div>


        {view === 'dashboard' ? (
          <section className="bg-white pt-32 pb-12 px-6 sm:px-12 min-h-screen">
             <div className="flex items-center justify-between mb-12 border-b border-slate-100 pb-6">
                <div>
                   <h2 className="text-slate-900 text-2xl font-bold tracking-tight">Oportunidades de Venta</h2>
                   <p className="text-slate-400 text-sm mt-1">Últimas propiedades detectadas en Milanuncios e Idealista.</p>
                </div>
                <div className="flex items-center gap-3">
                   <button 
                    onClick={fetchProperties}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-bold rounded-lg border border-slate-200 transition-colors disabled:opacity-50"
                   >
                     <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Actualizar
                   </button>
                   <div className="w-px h-6 bg-slate-200 mx-2" />
                   <div className="flex bg-slate-100 p-1 rounded-lg">
                      <button 
                        onClick={() => setFilter('all')}
                        className={`px-3 py-1.5 text-[10px] font-bold rounded-md transition-all ${filter === 'all' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}
                      >
                        TODOS
                      </button>
                      <button 
                        onClick={() => setFilter('hot')}
                        className={`px-3 py-1.5 text-[10px] font-bold rounded-md transition-all ${filter === 'hot' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}
                      >
                        TOP SCORE
                      </button>
                   </div>
                </div>
             </div>

             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              <AnimatePresence mode="popLayout">
                {filteredProperties.map((prop, idx) => (
                  <motion.div
                    key={prop.id}
                    layout
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex flex-col group cursor-pointer"
                  >
                    <div className="relative aspect-[4/3] rounded-lg overflow-hidden bg-slate-100 shadow-sm mb-3">
                      <img 
                        src={prop.images?.[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000&auto=format&fit=crop'} 
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                      />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                         <button className="w-10 h-10 bg-white text-slate-900 rounded-full flex items-center justify-center hover:bg-dribbble-accent hover:text-white transition-colors">
                            <Eye size={18} />
                         </button>
                      </div>
                      {prop.opportunity_score >= 80 && (
                        <div className="absolute top-3 right-3 bg-orange-500 text-white text-[10px] font-bold px-2 py-1 rounded">HOT</div>
                      )}
                    </div>
                    <div className="flex justify-between items-start">
                       <div className="flex flex-col">
                          <h3 className="text-slate-900 font-semibold text-sm leading-tight line-clamp-1">{prop.title}</h3>
                          <p className="text-slate-400 text-xs mt-1 flex items-center gap-1">
                             <MapPin size={10} /> {prop.city}
                          </p>
                       </div>
                       <div className="text-sm font-bold text-slate-900">
                          {prop.price.toLocaleString('es-ES')}€
                       </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
             </div>

             {/* Pagination Mockup */}
             <div className="mt-16 flex justify-end">
                <div className="flex items-center gap-4 bg-slate-50 px-4 py-2 rounded-lg border border-slate-100 text-slate-400 text-sm font-medium">
                   Next <ChevronRight size={16} />
                </div>
             </div>
          </section>
        ) : (
          <SettingsView insforge={insforge} />
        )}
      </main>
    </div>
  )
}

export default App
