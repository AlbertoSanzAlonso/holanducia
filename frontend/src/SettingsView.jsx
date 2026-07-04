import { useState, useEffect } from 'react'
import { Save, RefreshCw, Plus, X, Globe, Settings2, Database, Sparkles, AlertTriangle, Square, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from './api'

export default function SettingsView() {
  const [settings, setSettings] = useState({
    cities: [],
    max_price: 300000,
    min_rooms: 2,
    min_size_m2: 60,
    portals: 'Facebook',
    max_leads_per_portal: 10,
    mass_scrape_target: 500,
    mass_fb_scroll_steps: 100,
    facebook_groups: [],
    facebook_group_names: {},
  })
  const [dbStats, setDbStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [embeddingBusy, setEmbeddingBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showFBModal, setShowFBModal] = useState(false)
  const [newGroup, setNewGroup] = useState('')

  const AVAILABLE_PORTALS = ['Fotocasa', 'Habitaclia', 'Pisos.com', 'Facebook', 'Catastro']

  useEffect(() => {
    fetchSettings()
    refreshStats()
    fetchJobs()
    const interval = setInterval(fetchJobs, 10000)
    return () => clearInterval(interval)
  }, [])

  const refreshStats = async () => {
    setStatsLoading(true)
    try {
      const stats = await api.getDatabaseStats()
      setDbStats(stats)
    } catch {
      setDbStats(null)
    } finally {
      setStatsLoading(false)
    }
  }

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const data = await api.getSettings()
      if (data) setSettings({
          ...data,
          cities: data.cities || [],
          facebook_groups: data.facebook_groups || [],
          facebook_group_names: data.facebook_group_names || {},
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    const { id, updated_at, ...payload } = settings
    await api.saveSettings(payload)
    setSaving(false)
  }

  const togglePortal = (portal) => {
    const currentPortals = settings.portals ? settings.portals.split(',').map(p => p.trim()) : []
    const updated = currentPortals.includes(portal)
      ? currentPortals.filter(p => p !== portal)
      : [...currentPortals, portal]
    setSettings({ ...settings, portals: updated.join(', ') })
  }

  const addGroup = () => {
    if (!newGroup) return
    // Limpiar si pegan la URL completa
    const cleanId = newGroup.replace('https://www.facebook.com/groups/', '').replace('https://m.facebook.com/groups/', '').split('/')[0].split('?')[0]
    if (!settings.facebook_groups.includes(cleanId)) {
      setSettings({ ...settings, facebook_groups: [...settings.facebook_groups, cleanId] })
    }
    setNewGroup('')
  }

  const removeGroup = (id) => {
    setSettings({ ...settings, facebook_groups: settings.facebook_groups.filter(g => g !== id) })
  }

  const [notification, setNotification] = useState(null)
  const [jobs, setJobs] = useState([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [selectedJob, setSelectedJob] = useState(null)

  const buildPortalUrls = (cfg) => {
    const cities = cfg.cities?.length ? cfg.cities : ['malaga']
    const portals = (cfg.portals || '')
      .split(',')
      .map((p) => p.trim().toLowerCase())
      .filter(Boolean)
    const urls = []
    for (const city of cities) {
      const slug = city.toLowerCase().replace(/\s+/g, '-')
      if (portals.some((p) => p.includes('fotocasa'))) {
        urls.push(`https://www.fotocasa.es/es/comprar/viviendas/${slug}-provincia/todas-las-zonas/l`)
      }
      if (portals.some((p) => p.includes('habitaclia'))) {
        urls.push(`https://www.habitaclia.com/viviendas-${slug}.htm`)
      }
      if (portals.some((p) => p.includes('pisos'))) {
        urls.push(`https://www.pisos.com/venta/pisos-${slug}/`)
      }
    }
    return [...new Set(urls)]
  }

  const handleManualUpdate = async () => {
    setSaving(true)
    await handleSave()

    const portals = (settings.portals || '')
      .split(',')
      .map((p) => p.trim().toLowerCase())
      .filter(Boolean)
    const facebookOn = portals.includes('facebook')

    await api.createScrapingRequest({
      status: 'pending',
      source_name: 'Manual Trigger',
      target_leads: settings.max_leads_per_portal || 10,
      portal_urls: buildPortalUrls(settings),
      groups: facebookOn ? (settings.facebook_groups || []) : [],
    })

    const sources = portals.filter((p) => p !== 'catastro').join(', ') || 'sin fuentes'
    setNotification('Radar rápido activado — ' + (settings.max_leads_per_portal || 10) + ' anuncios · ' + sources)
    setTimeout(() => setNotification(null), 5000)
    setSaving(false)
  }

  const handleMassScrape = async () => {
    setSaving(true)
    await handleSave()

    await api.createScrapingRequest({
      status: 'pending',
      source_name: 'mass_scrape',
      target_leads: settings.mass_scrape_target || 500,
    })

    setNotification(
      '🔄 Scraping MASIVO encolado — cuota ' + (settings.mass_scrape_target || 500) +
      ' · compara todas las fuentes con la BD'
    )
    setTimeout(() => setNotification(null), 6000)
    setSaving(false)
    refreshStats()
  }

  const fetchJobs = async () => {
    setJobsLoading(true)
    try {
      const data = await api.listScrapingRequests()
      setJobs(data || [])
    } catch {
      setJobs([])
    } finally {
      setJobsLoading(false)
    }
  }

  const cancelAll = async () => {
    try {
      const res = await api.cancelAllPending()
      setNotification(`${res.cancelled} misiones canceladas`)
      setTimeout(() => setNotification(null), 4000)
    } catch {
      setNotification('Error al cancelar misiones')
      setTimeout(() => setNotification(null), 4000)
    }
    fetchJobs()
    refreshStats()
  }
    try {
      await api.cancelScrapingRequest(id)
    } catch {
      // 400 = ya completada/cancelada, solo refrescar
    }
    fetchJobs()
    refreshStats()
  }

  const statusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={16} className="text-emerald-500" />
      case 'processing': return <Loader2 size={16} className="text-blue-500 animate-spin" />
      case 'cancelled': return <XCircle size={16} className="text-slate-400" />
      default: return <Clock size={16} className="text-amber-500" />
    }
  }

  const statusLabel = (status) => {
    switch (status) {
      case 'completed': return 'Completada'
      case 'processing': return 'En proceso'
      case 'cancelled': return 'Cancelada'
      default: return 'Pendiente'
    }
  }

  const handleEmbedSync = async () => {
    setEmbeddingBusy(true)
    try {
      let total = 0
      let remaining = 1
      let rounds = 0
      while (remaining > 0 && rounds < 10) {
        const res = await api.embedBackfill(500)
        if (!res?.available) {
          setNotification(res?.message || 'Vectorial no disponible — configura OPENAI_API_KEY en el servicio API.')
          setTimeout(() => setNotification(null), 8000)
          break
        }
        total += res.embedded || 0
        remaining = res.remaining ?? 0
        rounds += 1
        if ((res.embedded || 0) === 0) break
      }
      await refreshStats()
      setNotification(
        total > 0
          ? `✓ ${total} propiedades sincronizadas con la BD vectorial${remaining > 0 ? ` · quedan ${remaining}` : ''}`
          : 'Todas las propiedades activas ya tienen vector'
      )
      setTimeout(() => setNotification(null), 7000)
    } catch (e) {
      setNotification('Error al vectorizar: ' + (e.message || 'revisa OPENAI_API_KEY en la API'))
      setTimeout(() => setNotification(null), 8000)
    } finally {
      setEmbeddingBusy(false)
    }
  }

  if (loading) return <div className="p-12 text-slate-400 font-medium italic">Sincronizando sistemas...</div>

  return (
    <div className="p-8 lg:p-12 max-w-2xl animate-in fade-in duration-500 pb-32">
      {/* Notificación Nativa Premium */}
      <AnimatePresence>
        {notification && (
          <motion.div 
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className="fixed top-8 left-1/2 -translate-x-1/2 z-[100] bg-slate-900 text-white px-8 py-5 rounded-3xl shadow-2xl border border-white/10 flex items-center gap-4 min-w-[400px]"
          >
            <div className="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center animate-pulse">
                <RefreshCw size={20} className="text-white" />
            </div>
            <div>
                <p className="text-white font-black text-sm uppercase tracking-widest italic">{notification}</p>
                <div className="h-1 bg-emerald-500 mt-2 rounded-full animate-[progress_5s_linear]" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-12">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Configuración</h1>
          <p className="text-slate-400 text-sm mt-2 font-medium">Controla las fuentes y filtros de inteligencia</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button 
            onClick={handleManualUpdate}
            disabled={saving}
            className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-4 rounded-2xl flex items-center justify-center gap-3 text-xs font-black uppercase tracking-widest transition-all shadow-xl shadow-emerald-500/20 active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={saving ? "animate-spin" : ""} size={18} />
            Radar rápido
          </button>
          <button 
            onClick={handleMassScrape}
            disabled={saving}
            className="flex-1 bg-[#0f172a] hover:bg-black text-white px-6 py-4 rounded-2xl flex items-center justify-center gap-3 text-xs font-black uppercase tracking-widest transition-all shadow-xl active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={saving ? "animate-spin" : ""} size={18} />
            Scraping masivo
          </button>
        </div>
      </div>
      
      <div className="space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-200/50">
        <div>
          <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Ciudades de rastreo</label>
          <input 
            type="text" 
            placeholder="Ej: malaga benalmadena (usa espacios)"
            value={(settings.cities || []).join(' ')} 
            onChange={(e) => setSettings({...settings, cities: e.target.value ? e.target.value.split(/\s+/).filter(s => s.trim()) : []})}
            className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold text-slate-700"
          />
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-4">Fuentes de Datos</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {AVAILABLE_PORTALS.map(portal => (
              <div key={portal} className="relative group">
                <label 
                  className={`flex items-center gap-3 p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                    (settings.portals || '').includes(portal) 
                      ? 'border-[#00acee] bg-blue-50/50 text-[#00acee]' 
                      : 'border-slate-50 bg-slate-50/50 text-slate-500 hover:border-slate-200'
                  }`}
                >
                  <input 
                    type="checkbox"
                    className="hidden"
                    checked={(settings.portals || '').includes(portal)}
                    onChange={() => togglePortal(portal)}
                  />
                  <span className="font-bold text-xs uppercase tracking-tight">{portal}</span>
                </label>
                {portal === 'Facebook' && (
                  <button 
                    onClick={() => setShowFBModal(true)}
                    className="absolute -top-2 -right-2 bg-slate-900 text-white p-1.5 rounded-full shadow-lg hover:scale-110 transition-all z-10"
                    title="Gestionar Grupos"
                  >
                    <Settings2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Radar rápido (anuncios)</label>
            <input 
              type="number" 
              value={settings.max_leads_per_portal || 10} 
              onChange={(e) => setSettings({...settings, max_leads_per_portal: parseInt(e.target.value)})}
              className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-black text-blue-600"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Scraping masivo (cuota)</label>
            <input 
              type="number" 
              value={settings.mass_scrape_target || 500} 
              onChange={(e) => setSettings({...settings, mass_scrape_target: parseInt(e.target.value)})}
              className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#0f172a] focus:bg-white outline-none transition-all font-black text-slate-900"
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Scroll Facebook en modo masivo (pasos)</label>
          <input 
            type="number" 
            value={settings.mass_fb_scroll_steps || 100} 
            onChange={(e) => setSettings({...settings, mass_fb_scroll_steps: parseInt(e.target.value)})}
            className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#0f172a] focus:bg-white outline-none transition-all font-bold"
          />
          <p className="text-xs text-slate-400 mt-2">Más pasos = más posts leídos por grupo. Recomendado: 100–150 para sync completo.</p>
        </div>

        {dbStats && (
          <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-[#0f172a] text-white">
                  <Database size={18} />
                </div>
                <div>
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Estado de la base de datos</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Vector: {dbStats.total_embedded ?? 0} indexadas
                    {dbStats.embedding_model ? ` · ${dbStats.embedding_model}` : ''}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={refreshStats}
                disabled={statsLoading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-white transition-all"
              >
                <RefreshCw size={14} className={statsLoading ? 'animate-spin' : ''} />
                Actualizar
              </button>
            </div>

            {!dbStats.embedding_available && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900">
                <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                <p className="text-xs font-semibold leading-relaxed">
                  La BD vectorial está desactivada: falta <code className="text-[10px] bg-amber-100 px-1 rounded">OPENAI_API_KEY</code> en el contenedor <strong>api</strong> (Coolify). Sin ella no hay deduplicación semántica ni búsqueda por similitud.
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-center">
              <div><p className="text-2xl font-black text-slate-900">{dbStats.total_active}</p><p className="text-[10px] text-slate-400 uppercase">Activos</p></div>
              <div><p className="text-2xl font-black text-slate-400">{dbStats.total_inactive}</p><p className="text-[10px] text-slate-400 uppercase">Bajas</p></div>
              <div><p className="text-2xl font-black text-emerald-600">{dbStats.total_embedded ?? 0}</p><p className="text-[10px] text-slate-400 uppercase">Con vector</p></div>
              <div><p className="text-2xl font-black text-blue-600">{dbStats.without_embedding}</p><p className="text-[10px] text-slate-400 uppercase">Sin vector</p></div>
              <div><p className="text-2xl font-black text-amber-600">{dbStats.stale_7d}</p><p className="text-[10px] text-slate-400 uppercase">Sin ver 7d</p></div>
            </div>

            {dbStats.sync_in_progress && (
              <p className="text-xs font-bold text-[#00acee]">
                Sync en curso (#{dbStats.sync_in_progress.id}) desde {new Date(dbStats.sync_in_progress.started_at).toLocaleString('es-ES')}
              </p>
            )}

            {dbStats.last_sync?.stats && (
              <p className="text-xs text-slate-500">
                Último sync completado: +{dbStats.last_sync.stats.created || 0} creados ·{' '}
                {dbStats.last_sync.stats.updated || 0} actualizados ·{' '}
                {dbStats.last_sync.stats.deactivated || 0} bajas
              </p>
            )}

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={handleEmbedSync}
                disabled={embeddingBusy || !dbStats.embedding_available}
                className="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-black uppercase tracking-widest transition-all disabled:opacity-40"
              >
                <Sparkles size={16} className={embeddingBusy ? 'animate-pulse' : ''} />
                {embeddingBusy ? 'Vectorizando…' : 'Sincronizar BD vectorial'}
              </button>
              <button
                type="button"
                onClick={handleMassScrape}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl bg-[#0f172a] hover:bg-black text-white text-[10px] font-black uppercase tracking-widest transition-all disabled:opacity-50"
              >
                <RefreshCw size={16} className={saving ? 'animate-spin' : ''} />
                Scraping masivo
              </button>
            </div>
          </div>
        )}

        {/* MISIONES DE SCRAPING */}
        <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-amber-500 text-white">
                <Clock size={18} />
              </div>
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Misiones de scraping</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={cancelAll}
                className="flex items-center gap-1 px-3 py-2 rounded-xl bg-red-50 hover:bg-red-100 border border-red-200 text-[10px] font-black uppercase tracking-widest text-red-500 transition-all"
              >
                <Square size={12} />
                Cancelar todas
              </button>
              <button
                type="button"
                onClick={fetchJobs}
                disabled={jobsLoading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-white transition-all"
              >
                <RefreshCw size={14} className={jobsLoading ? 'animate-spin' : ''} />
                Actualizar
              </button>
            </div>
          </div>

          {jobs.length === 0 ? (
            <p className="text-xs text-slate-400 font-medium text-center py-4">No hay misiones recientes</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => setSelectedJob(job)}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer hover:shadow-md ${
                    job.status === 'processing'
                      ? 'bg-blue-50/50 border-blue-200 hover:border-blue-300'
                      : job.status === 'completed'
                      ? 'bg-white border-slate-100 hover:border-slate-300'
                      : 'bg-white border-slate-100 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {statusIcon(job.status)}
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-700 truncate">
                        #{job.id} {job.source_name || 'Scraping'}
                      </p>
                      <p className="text-[10px] text-slate-400 font-medium">
                        {statusLabel(job.status)}
                        {job.status === 'completed' && job.error_message && (
                          <span className="ml-1 text-emerald-600"> · {job.error_message.split('—')[0]}</span>
                        )}
                        {job.target_leads ? ` · cuota ${job.target_leads}` : ''}
                        {job.groups?.length ? ` · ${job.groups.length} grupos` : ''}
                        {job.portal_urls?.length ? ` · ${job.portal_urls.length} portales` : ''}
                      </p>
                    </div>
                  </div>
                  {(job.status === 'pending' || job.status === 'processing') && (
                    <button
                      onClick={() => cancelJob(job.id)}
                      className="shrink-0 p-2 rounded-lg bg-red-50 hover:bg-red-100 text-red-500 transition-all"
                      title="Cancelar misión"
                    >
                      <Square size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* MODAL DETALLE MISIÓN */}
        <AnimatePresence>
          {selectedJob && (
            <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setSelectedJob(null)}>
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white w-full max-w-lg rounded-[2.5rem] p-10 shadow-2xl max-h-[85vh] overflow-y-auto"
              >
                <div className="flex justify-between items-start mb-8">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {statusIcon(selectedJob.status)}
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                        {statusLabel(selectedJob.status)}
                      </span>
                    </div>
                    <h2 className="text-2xl font-black text-slate-900">Misión #{selectedJob.id}</h2>
                    <p className="text-sm text-slate-500 font-medium mt-1">{selectedJob.source_name || 'Scraping'}</p>
                  </div>
                  <button
                    onClick={() => setSelectedJob(null)}
                    className="bg-slate-100 hover:bg-slate-200 p-2 rounded-full transition-all"
                  >
                    <X size={20} />
                  </button>
                </div>

                <div className="space-y-5">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 rounded-2xl">
                      <p className="text-[10px] uppercase tracking-widest font-black text-slate-400 mb-1">Cuota</p>
                      <p className="text-xl font-black text-slate-900">{selectedJob.target_leads || '—'}</p>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-2xl">
                      <p className="text-[10px] uppercase tracking-widest font-black text-slate-400 mb-1">Solicitada</p>
                      <p className="text-sm font-bold text-slate-700">
                        {new Date(selectedJob.requested_at).toLocaleString('es-ES')}
                      </p>
                    </div>
                  </div>

                  {selectedJob.processed_at && (
                    <div className="p-4 bg-slate-50 rounded-2xl">
                      <p className="text-[10px] uppercase tracking-widest font-black text-slate-400 mb-1">
                        {selectedJob.status === 'completed' ? 'Completada' : 'Procesada'}
                      </p>
                      <p className="text-sm font-bold text-slate-700">
                        {new Date(selectedJob.processed_at).toLocaleString('es-ES')}
                      </p>
                    </div>
                  )}

                  {selectedJob.portal_urls?.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-widest font-black text-slate-400 mb-2">
                        Portales ({selectedJob.portal_urls.length})
                      </p>
                      <div className="space-y-1.5 max-h-40 overflow-y-auto">
                        {selectedJob.portal_urls.map((url, i) => {
                          const domain = url.replace(/https?:\/\/(www\.)?/, '').split('/')[0]
                          const label = domain === 'fotocasa.es' ? 'Fotocasa' :
                                        domain === 'habitaclia.com' ? 'Habitaclia' :
                                        domain === 'pisos.com' ? 'Pisos.com' :
                                        domain === 'idealista.com' ? 'Idealista' : domain
                          return (
                            <div key={i} className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-xl">
                              <span className="text-[10px] font-black uppercase text-slate-500 bg-slate-200 px-2 py-0.5 rounded-md">{label}</span>
                              <span className="text-[10px] text-slate-400 truncate font-medium">{url}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {selectedJob.groups?.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-widest font-black text-slate-400 mb-2">
                        Grupos Facebook ({selectedJob.groups.length})
                      </p>
                      <div className="space-y-1.5 max-h-40 overflow-y-auto">
                        {selectedJob.groups.map((g, i) => {
                          const name = settings.facebook_group_names?.[g]
                          return (
                            <div key={i} className="p-2.5 bg-slate-50 rounded-xl">
                              <p className="text-[10px] text-slate-500 font-medium truncate">
                                {name || `facebook.com/groups/${g}`}
                              </p>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {selectedJob.error_message && (
                    <div className={`p-4 rounded-2xl ${selectedJob.status === 'completed' ? 'bg-emerald-50 border border-emerald-200' : selectedJob.status === 'processing' ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border border-red-200'}`}>
                      <p className="text-[10px] uppercase tracking-widest font-black text-slate-500 mb-1">
                        {selectedJob.status === 'processing' ? 'Estado' : 'Resultado'}
                      </p>
                      <p className="text-xs font-medium text-slate-700">{selectedJob.error_message}</p>
                    </div>
                  )}

                  {(selectedJob.status === 'pending' || selectedJob.status === 'processing') && (
                    <button
                      onClick={() => { cancelJob(selectedJob.id); setSelectedJob(null) }}
                      className="w-full py-4 rounded-2xl bg-red-500 hover:bg-red-600 text-white font-black uppercase tracking-widest text-xs transition-all flex items-center justify-center gap-2"
                    >
                      <Square size={16} />
                      Cancelar misión
                    </button>
                  )}
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Precio máximo (€)</label>
            <input 
              type="number" 
              value={settings.max_price} 
              onChange={(e) => setSettings({...settings, max_price: parseInt(e.target.value)})}
              className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Habitaciones mín.</label>
            <input 
              type="number" 
              value={settings.min_rooms || 2} 
              onChange={(e) => setSettings({...settings, min_rooms: parseInt(e.target.value)})}
              className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold"
            />
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full mt-4 bg-slate-900 hover:bg-black text-white font-black py-5 rounded-[2rem] shadow-2xl shadow-slate-900/20 flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-50 uppercase tracking-widest text-xs"
        >
          {saving ? <RefreshCw className="animate-spin" size={20} /> : <Save size={20} />}
          Guardar Configuración
        </button>
      </div>

      {/* MODAL DE FACEBOOK GRUPOS */}
      {showFBModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-lg rounded-[2.5rem] p-10 shadow-2xl animate-in zoom-in-95 duration-300">
            <div className="flex justify-between items-start mb-8">
              <div>
                <div className="flex items-center gap-2 text-blue-600 mb-1">
                  <Globe size={20} />
                  <span className="text-[10px] font-black uppercase tracking-widest">Infiltración Social</span>
                </div>
                <h2 className="text-2xl font-black text-slate-900">Grupos de Facebook</h2>
              </div>
              <button 
                onClick={() => setShowFBModal(false)}
                className="bg-slate-100 hover:bg-slate-200 p-2 rounded-full transition-all"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-6">
              <div className="relative">
                <input 
                  type="text"
                  placeholder="ID o nombre del grupo..."
                  value={newGroup}
                  onChange={(e) => setNewGroup(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addGroup()}
                  className="w-full pl-6 pr-16 py-4 bg-slate-100 rounded-2xl border-2 border-transparent focus:border-blue-500 focus:bg-white outline-none transition-all font-bold"
                />
                <button 
                  onClick={addGroup}
                  className="absolute right-2 top-2 bottom-2 bg-blue-600 text-white px-4 rounded-xl hover:bg-blue-700 transition-all font-bold flex items-center gap-1"
                >
                  <Plus size={18} />
                </button>
              </div>

              <div className="flex flex-wrap gap-2 min-h-[100px] p-4 bg-slate-50 rounded-3xl border border-dashed border-slate-200">
                {settings.facebook_groups.length === 0 && (
                  <p className="text-slate-400 text-xs font-medium m-auto">No hay grupos añadidos</p>
                )}
                {settings.facebook_groups.map(id => {
                  const name = settings.facebook_group_names?.[id]
                  return (
                    <div key={id} className="bg-white border border-slate-100 px-4 py-2 rounded-xl flex items-center gap-3 shadow-sm group hover:border-blue-200 transition-all animate-in zoom-in-90">
                      <div className="flex flex-col">
                        {name && <span className="text-xs font-black text-slate-700 truncate max-w-[180px]">{name}</span>}
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">ID: {id}</span>
                      </div>
                      <button 
                        onClick={() => removeGroup(id)}
                        className="text-slate-300 hover:text-red-500 transition-all"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )
                })}
              </div>

              <button 
                onClick={() => setShowFBModal(false)}
                className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold hover:bg-black transition-all"
              >
                Listo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
