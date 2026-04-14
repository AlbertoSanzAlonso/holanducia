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
    if (filter === 'hot') return p.opportunity_score >= 80
    if (filter === 'particular') return p.is_individual
    return true
  })

  return (
    <div className="flex min-h-screen bg-[#f3f4f6]">
      {/* Sidebar - Dribbble Style */}
      <aside className="w-72 bg-[#1e2432] text-white flex flex-col fixed h-full shrink-0">
        <div className="p-8 flex flex-col items-center border-b border-[#ffffff08]">
          <div className="relative mb-4">
            <img 
              src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=200" 
              className="w-24 h-24 rounded-full border-4 border-[#ffffff10] object-cover"
              alt="Profile"
            />
            <div className="absolute bottom-1 right-1 w-5 h-5 bg-green-500 rounded-full border-2 border-[#1e2432]" />
          </div>
          <h2 className="text-xl font-bold">ANGELA HOLAND</h2>
          <p className="text-slate-400 text-xs mt-1 uppercase tracking-widest">Real Estate Specialist</p>
          <div className="border-t border-[#ffffff10] w-full my-6" />
          <button className="bg-[#00acee] hover:bg-[#009bd6] transition-colors text-white text-sm font-bold py-2 px-8 rounded-full shadow-lg shadow-[#00acee30]">
            Captar Ahora
          </button>
        </div>

        <nav className="flex-1 mt-4">
          <button 
            onClick={() => setFilter('all')}
            className={`w-full sidebar-link ${filter === 'all' ? 'active' : ''}`}
          >
            <LayoutDashboard size={18} /> Portfolio
          </button>
          <button 
            onClick={() => setFilter('hot')}
            className={`w-full sidebar-link ${filter === 'hot' ? 'active' : ''}`}
          >
            <Flame size={18} /> Oportunidades
          </button>
          <button 
            onClick={() => { setView('dashboard'); setFilter('particular'); }}
            className={`w-full sidebar-link ${filter === 'particular' && view === 'dashboard' ? 'active' : ''}`}
          >
            <User size={18} /> Mis Blogs
          </button>
          <div className="border-t border-[#ffffff10] my-4 mx-8" />
          <button 
            onClick={() => setView('settings')}
            className={`w-full sidebar-link ${view === 'settings' ? 'active' : ''}`}
          >
            <RefreshCw size={18} /> Configuración
          </button>
          <button className="w-full sidebar-link">
             <Mail size={18} /> Mensajes
          </button>
        </nav>

        <div className="p-8 mt-auto flex justify-between items-center text-slate-500">
           <MoreHorizontal className="cursor-pointer hover:text-white" />
        </div>
      </aside>

      {/* Content Area */}
      <main className="ml-72 flex-1 flex flex-col">
        {/* Top Header - Dribbble Style */}
        <div className="relative h-96 bg-[#2d3446] overflow-hidden">
          {/* Background Image/Pattern */}
          <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=2000')] bg-cover bg-center mix-blend-overlay opacity-30" />
          
          <div className="relative z-10 w-full px-12 py-8 flex justify-between items-start text-white/80 text-sm">
             <div className="flex items-center gap-2">
                <Mail size={16} /> holand@ia.com
             </div>
             <div className="flex items-center gap-4">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors cursor-pointer">
                  <User size={14} />
                </div>
             </div>
          </div>

          <div className="relative z-10 flex flex-col items-center justify-center h-full -mt-12">
            <h1 className="text-5xl font-light text-white tracking-tight text-center">
              Better experience from <br/> <strong className="font-bold">better AI analysis.</strong>
            </h1>
          </div>

          {/* User Initial Circle in Header */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 z-20">
             <div className="w-16 h-16 bg-[#1e2432] rounded-full border-4 border-white flex items-center justify-center shadow-xl">
                <span className="text-white font-serif italic text-2xl">AH</span>
             </div>
          </div>
        </div>

        {view === 'dashboard' ? (
          <section className="bg-white pt-16 pb-12 px-12">
             <div className="flex items-center justify-between mb-10 border-b border-slate-100 pb-4">
                <h2 className="text-slate-400 font-medium flex items-center gap-2">
                   <div className="w-2 h-2 rounded-full border-2 border-slate-300" />
                   Recent Opportunities from Portals
                </h2>
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
