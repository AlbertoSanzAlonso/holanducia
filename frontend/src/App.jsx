import { useState, useEffect } from 'react'
import { api, API_URL } from './api'
import { 
  MapPin, Flame, User, LayoutDashboard, Filter, RefreshCw,
  Eye, Mail, MoreHorizontal, ChevronRight, ChevronLeft, Menu, X,
  ShieldCheck, AlertTriangle, Trash2, CheckCircle2, FolderHeart, Tag,
  BarChart3, Settings as SettingsIcon, LayoutGrid, ListPlus, Edit3, Bookmark, Images
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import PropertyIntelligenceModal from './PropertyIntelligenceModal'
import AdvisorChat from './AdvisorChat'
import SettingsView from './SettingsView'
import StatisticsView from './StatisticsView'
import PropertyFilters from './PropertyFilters'
import ListEditModal from './ListEditModal'
import PropertyGallery, { getPropertyImageUrls } from './PropertyGallery'
import { formatPrice, getListingUrl, hasPropertyImage } from './utils/propertyDisplay'
import {
  DEFAULT_FILTERS,
  applyPropertyFilters,
  getUniqueCities,
  getUniqueSources,
  countActiveFilters,
} from './utils/propertyFilters'

function App() {
  const [properties, setProperties] = useState([])
  const [categories, setCategories] = useState([])
  const [lists, setLists] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [selectedCategoryId, setSelectedCategoryId] = useState(null)
  const [selectedListId, setSelectedListId] = useState(null)
  const [listModal, setListModal] = useState(null)
  const [view, setView] = useState('dashboard')
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [filtersExpanded, setFiltersExpanded] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20
  const [selectedProperty, setSelectedProperty] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [errorField, setErrorField] = useState(null)
  const [securityBlock, setSecurityBlock] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    setErrorField(null)
    try {
        const [propsData, catsData, listsData] = await Promise.all([
          api.getProperties(),
          api.getCategories(),
          api.getLists().catch(() => []),
        ])
        setProperties(Array.isArray(propsData) ? propsData : [])
        setCategories(Array.isArray(catsData) ? catsData : [])
        setLists(Array.isArray(listsData) ? listsData : [])
    } catch (e) {
        setErrorField(`No se pudo conectar con la API (${API_URL || 'proxy /api en Vercel'}). Si usas HTTP en el VPS, deja VITE_API_URL vacía y redeploy.`)
        console.error('fetchData:', e)
    } finally {
        setLoading(false)
    }
  }

  const updateProperty = async (updatedProp) => {
    const { id, created_at, updated_at, ...data } = updatedProp
    await api.updateProperty(id, data)
    fetchData()
  }

  const deleteProperty = async (id) => {
    await api.deleteProperty(id)
    setSelectedIds(prev => { const n = new Set(prev); n.delete(id); return n; })
    fetchData()
  }

  const deleteBatch = async () => {
    if (!window.confirm(`¿Seguro que quieres eliminar ${selectedIds.size} elementos?`)) return
    await api.deleteProperties(Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
  }

  const changeBatchCategory = async (catId) => {
    await api.updatePropertiesCategory(Array.from(selectedIds), catId)
    setSelectedIds(new Set())
    fetchData()
  }

  const addSelectionToList = async (listId) => {
    await api.addToList(listId, Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
  }

  const removeSelectionFromList = async () => {
    if (!selectedListId) return
    await api.removeFromList(selectedListId, Array.from(selectedIds))
    setSelectedIds(new Set())
    fetchData()
  }

  const saveList = async (data) => {
    if (listModal?.list?.id) {
      await api.updateList(listModal.list.id, data)
    } else {
      const created = await api.createList(data)
      setSelectedListId(created.id)
      setSelectedCategoryId(null)
    }
    fetchData()
  }

  const deleteList = async (id) => {
    await api.deleteList(id)
    if (selectedListId === id) setSelectedListId(null)
    fetchData()
  }

  const addPropertyToList = async (listId, propertyId) => {
    await api.addToList(listId, [propertyId])
    fetchData()
  }

  const removePropertyFromList = async (listId, propertyId) => {
    await api.removeFromList(listId, [propertyId])
    fetchData()
  }

  const checkScrapingStatus = async () => {
    try {
      const data = await api.getLatestScrapingRequest()
      if (data?.status === 'security_block') {
        setSecurityBlock(data)
      } else {
        setSecurityBlock(null)
      }
    } catch {
      setSecurityBlock(null)
    }
  }

  useEffect(() => { 
    fetchData()
    const interval = setInterval(checkScrapingStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    setCurrentPage(1)
  }, [filters, filter, selectedCategoryId, selectedListId])

  const selectedList = lists.find((l) => l.id === selectedListId) || null
  const listPropertyIds = selectedList?.property_ids ?? null

  const cityOptions = getUniqueCities(properties)
  const sourceOptions = getUniqueSources(properties)
  const activeFilterCount = countActiveFilters(filters)

  const filteredProperties = applyPropertyFilters(properties, filters, {
    filter,
    selectedCategoryId,
    listPropertyIds,
  })

  const paginatedProperties = filteredProperties.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS)
    setFilter('all')
    setSelectedCategoryId(null)
    setSelectedListId(null)
    setCurrentPage(1)
  }

  const emptyMessage = (() => {
    if (loading) return null
    if (errorField) return errorField
    if (properties.length === 0) return 'No hay propiedades en la base de datos. Usa Configuración → Actualizar ahora para scrapear.'
    if (selectedListId) {
      return selectedList
        ? `La lista "${selectedList.name}" está vacía. Selecciona propiedades y añádelas con la barra de acciones.`
        : 'Lista no encontrada.'
    }
    if (selectedCategoryId) {
      const cat = categories.find(c => c.id === selectedCategoryId)
      return `Ninguna propiedad en "${cat?.name || 'esta categoría'}". Pulsa "Todo el Mercado" o asigna categorías desde el detalle de cada inmueble.`
    }
    if (filter === 'hot') return 'Ninguna oportunidad TOP (score ≥ 80). Prueba el filtro TODOS.'
    if (filter === 'particular') return 'Ningún anuncio de particular con los filtros actuales.'
    if (filters.sources?.length > 0) return `Ningún anuncio de ${filters.sources.join(', ')} con los filtros actuales.`
    if (activeFilterCount > 0) return 'Ningún anuncio coincide con los filtros aplicados. Prueba a ampliar el rango de precio o limpiar filtros.'
    return null
  })()

  return (
    <div className="flex min-h-screen bg-[#f8fafc] font-sans selection:bg-[#00acee] selection:text-white">
      {/* Sidebar Premium */}
      <aside className="hidden lg:flex w-80 bg-[#0f172a] text-white flex-col fixed h-full z-50 shadow-2xl">
        <SidebarContent 
            setView={setView} 
            setFilter={setFilter} 
            setSelectedCategoryId={setSelectedCategoryId}
            setSelectedListId={setSelectedListId}
            categories={categories}
            lists={lists}
            onCreateList={() => setListModal({ list: null })}
            onEditList={(list) => setListModal({ list })}
            view={view} 
            filter={filter} 
            selectedCategoryId={selectedCategoryId}
            selectedListId={selectedListId}
        />
      </aside>

      <main className="flex-1 flex flex-col lg:ml-80 min-w-0">
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
                   <h2 className="text-4xl lg:text-5xl font-black text-slate-900 tracking-tight">
                     {selectedList ? selectedList.name : 'Vigilante de Inversión'}
                   </h2>
                   <p className="text-slate-400 text-sm mt-3 font-bold uppercase tracking-[0.2em]">
                     {filteredProperties.length} oportunidades
                     {selectedList ? ` en esta lista` : ' encontradas'}
                   </p>
                   {selectedList?.description && (
                     <p className="text-slate-500 text-sm mt-2 max-w-xl">{selectedList.description}</p>
                   )}
                </div>
                <div className="flex items-center gap-4 flex-wrap">
                   {selectedList && (
                     <>
                       <button
                         onClick={() => setListModal({ list: selectedList })}
                         className="flex items-center gap-2 px-5 py-3 rounded-2xl border border-slate-200 text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-50"
                       >
                         <Edit3 size={16} /> Editar lista
                       </button>
                     </>
                   )}
                   <button onClick={fetchData} className="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-slate-400 hover:bg-white hover:shadow-xl transition-all">
                      <RefreshCw size={24} className={loading ? 'animate-spin' : ''} />
                   </button>
                   <div className="flex bg-slate-50 p-2 rounded-2xl border border-slate-100">
                      <button onClick={() => setFilter('all')} className={`px-6 py-2.5 text-[10px] font-black rounded-xl uppercase tracking-widest transition-all ${filter === 'all' ? 'bg-[#0f172a] text-white shadow-xl' : 'text-slate-500'}`}>TODOS</button>
                      <button onClick={() => setFilter('hot')} className={`px-6 py-2.5 text-[10px] font-black rounded-xl uppercase tracking-widest transition-all ${filter === 'hot' ? 'bg-[#0f172a] text-white shadow-xl' : 'text-slate-500'}`}>TOP</button>
                   </div>
                </div>
             </div>

             <PropertyFilters
               filters={filters}
               onChange={setFilters}
               onReset={resetFilters}
               cities={cityOptions}
               sources={sourceOptions}
               activeCount={activeFilterCount}
               expanded={filtersExpanded}
               onToggleExpanded={() => setFiltersExpanded((v) => !v)}
             />

             {emptyMessage && paginatedProperties.length === 0 && (
                <div className={`mb-12 p-8 rounded-3xl border-2 ${errorField ? 'bg-red-50 border-red-200 text-red-800' : 'bg-slate-50 border-slate-200 text-slate-600'}`}>
                  <p className="font-bold text-sm leading-relaxed">{emptyMessage}</p>
                  {(selectedCategoryId || filter !== 'all' || activeFilterCount > 0 || selectedListId) && !errorField && (
                    <button
                      onClick={resetFilters}
                      className="mt-4 text-xs font-black uppercase tracking-widest text-[#00acee] hover:underline"
                    >
                      Ver todo el mercado
                    </button>
                  )}
                </div>
             )}

             <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-12">
                {paginatedProperties.map((prop, idx) => (
                    <motion.div 
                        key={prop.id}
                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                        onClick={() => setSelectedProperty(prop)}
                        className={`group relative flex flex-col cursor-pointer ${selectedIds.has(prop.id) ? 'scale-[0.98]' : ''}`}
                    >
                        <div className={`relative aspect-[4/3] rounded-[2.5rem] overflow-hidden bg-slate-100 shadow-lg mb-6 border-4 transition-all ${selectedIds.has(prop.id) ? 'border-[#00acee]' : 'border-transparent'}`}>
                          <PropertyGallery images={prop.images} title={prop.title} variant="card" className="w-full h-full aspect-[4/3]" />
                          {getPropertyImageUrls(prop.images).length > 1 && (
                            <div className="absolute bottom-6 right-6 flex items-center gap-1.5 bg-black/50 text-white text-[9px] font-black px-3 py-1.5 rounded-full uppercase tracking-widest pointer-events-none">
                              <Images size={12} />
                              {getPropertyImageUrls(prop.images).length} fotos
                            </div>
                          )}
                          {!hasPropertyImage(prop) && (
                            <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-black/50 text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest">
                              Sin foto
                            </div>
                          )}
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
                           <div className="flex justify-between items-center gap-3">
                              <div className="flex items-center gap-4 text-slate-400 text-[10px] font-black uppercase tracking-widest min-w-0">
                                 <span className="flex items-center gap-1.5 truncate"><MapPin size={14} className="text-[#00acee] shrink-0" /> {prop.city || '—'}</span>
                                 {prop.size_m2 ? <span className="shrink-0">{prop.size_m2} m²</span> : null}
                              </div>
                              <div className={`text-lg font-black px-4 py-2 rounded-2xl shrink-0 ${Number(prop.price) > 0 ? 'text-slate-900 bg-slate-50' : 'text-slate-500 bg-slate-100'}`}>
                                {formatPrice(prop.price)}
                              </div>
                           </div>
                           {getListingUrl(prop) && (
                             <a
                               href={getListingUrl(prop)}
                               target="_blank"
                               rel="noreferrer"
                               onClick={(e) => e.stopPropagation()}
                               className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-[#00acee] hover:underline"
                             >
                               Ver anuncio
                             </a>
                           )}
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
        ) : view === 'stats' ? (
          <StatisticsView properties={properties} onPropertySelect={setSelectedProperty} />
        ) : (
          <SettingsView />
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
                    {selectedListId ? (
                      <button
                        onClick={removeSelectionFromList}
                        className="whitespace-nowrap px-5 py-3 rounded-2xl border border-red-400/30 bg-red-500/10 hover:bg-red-500 text-red-300 hover:text-white text-[10px] font-black uppercase tracking-widest transition-all"
                      >
                        Quitar de lista
                      </button>
                    ) : (
                      <>
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
                        <div className="flex gap-2 overflow-x-auto max-w-[280px] no-scroll-bar">
                          {lists.map((list) => (
                            <button
                              key={list.id}
                              onClick={() => addSelectionToList(list.id)}
                              style={{ borderColor: `${list.color}55` }}
                              className="whitespace-nowrap px-4 py-3 rounded-2xl border hover:bg-white/10 text-[10px] font-black uppercase tracking-widest transition-all"
                            >
                              + {list.name}
                            </button>
                          ))}
                          {lists.length === 0 && (
                            <button
                              onClick={() => setListModal({ list: null })}
                              className="whitespace-nowrap px-4 py-3 rounded-2xl border border-white/10 text-[10px] font-black uppercase tracking-widest"
                            >
                              Crear lista
                            </button>
                          )}
                        </div>
                      </>
                    )}
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
                lists={lists}
                onClose={() => setSelectedProperty(null)} 
                onUpdate={updateProperty}
                onDelete={deleteProperty}
                onAddToList={addPropertyToList}
                onRemoveFromList={removePropertyFromList}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {listModal && (
            <ListEditModal
              list={listModal.list}
              onClose={() => setListModal(null)}
              onSave={saveList}
              onDelete={deleteList}
            />
          )}
        </AnimatePresence>
      </main>
      <AdvisorChat />
    </div>
  )
}

function SidebarContent({ setView, setFilter, setSelectedCategoryId, setSelectedListId, categories, lists, onCreateList, onEditList, view, filter, selectedCategoryId, selectedListId }) {
  const handleMarket = () => {
    setView('dashboard')
    setFilter('all')
    setSelectedCategoryId(null)
    setSelectedListId(null)
  }

  const handleCategory = (catId) => {
    setView('dashboard')
    setFilter('all')
    setSelectedCategoryId(catId)
    setSelectedListId(null)
  }

  const handleList = (listId) => {
    setView('dashboard')
    setFilter('all')
    setSelectedCategoryId(null)
    setSelectedListId(listId)
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

      <nav className="flex-1 px-8 mt-12 space-y-3 overflow-y-auto">
        <p className="px-6 text-[10px] font-black text-white/20 uppercase tracking-[0.3em] mb-4">Radar Principal</p>
        <SidebarNavItem active={view === 'dashboard' && !selectedCategoryId && !selectedListId} icon={<LayoutGrid size={22} />} label="Todo el Mercado" onClick={handleMarket} />
        <SidebarNavItem active={view === 'stats'} icon={<BarChart3 size={22} />} label="Estadísticas" onClick={() => { setView('stats'); setSelectedCategoryId(null); setSelectedListId(null) }} />
        <SidebarNavItem active={view === 'settings'} icon={<SettingsIcon size={22} />} label="Configuración" onClick={() => setView('settings')} />
        
        <div className="py-10 px-6"><div className="h-px bg-white/5 w-full" /></div>

        <div className="flex items-center justify-between px-6 mb-4">
          <p className="text-[10px] font-black text-white/20 uppercase tracking-[0.3em]">Mis Listas</p>
          <button
            onClick={onCreateList}
            className="p-1.5 rounded-lg text-white/30 hover:text-white hover:bg-white/10 transition-all"
            title="Nueva lista"
          >
            <ListPlus size={18} />
          </button>
        </div>
        <div className="space-y-2 mb-6">
          {lists.length === 0 ? (
            <button
              onClick={onCreateList}
              className="w-full px-6 py-3 rounded-2xl border border-dashed border-white/10 text-white/30 text-[10px] font-black uppercase tracking-widest hover:border-white/20 hover:text-white/50 transition-all"
            >
              + Crear primera lista
            </button>
          ) : (
            lists.map((list) => (
              <div key={list.id} className="flex items-center gap-1 group">
                <SidebarNavItem
                  active={selectedListId === list.id}
                  icon={<Bookmark size={20} style={{ color: list.color }} />}
                  label={`${list.name} (${list.property_count})`}
                  onClick={() => handleList(list.id)}
                  className="flex-1 min-w-0"
                />
                <button
                  onClick={() => onEditList(list)}
                  className="p-2 rounded-xl text-white/20 hover:text-white hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                  title="Editar lista"
                >
                  <Edit3 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <p className="px-6 text-[10px] font-black text-white/20 uppercase tracking-[0.3em] mb-4">Mi Cartera</p>
        <div className="space-y-2">
            {categories.map(cat => (
                <SidebarNavItem 
                    key={cat.id}
                    active={selectedCategoryId === cat.id} 
                    icon={<Tag size={20} style={{ color: cat.color }} />} 
                    label={cat.name} 
                    onClick={() => handleCategory(cat.id)} 
                />
            ))}
        </div>
      </nav>
    </div>
  )
}

function SidebarNavItem({ active, icon, label, onClick, className = '' }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-5 px-6 py-4 rounded-2xl transition-all duration-500 ${active ? 'bg-gradient-to-r from-[#00acee] to-[#4f46e5] text-white shadow-2xl shadow-[#00acee/40]' : 'text-white/40 hover:text-white hover:bg-white/5'} ${className}`}
    >
      <span className={`shrink-0 ${active ? 'text-white' : 'text-white/20'}`}>{icon}</span>
      <span className="text-xs font-black uppercase tracking-widest truncate text-left">{label}</span>
    </button>
  )
}

export default App
