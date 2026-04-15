import { useState, useEffect } from 'react'
import { Save, RefreshCw, Plus, X, Facebook, Settings2 } from 'lucide-react'

export default function SettingsView({ insforge }) {
  const [settings, setSettings] = useState({
    cities: [],
    max_price: 300000,
    min_rooms: 2,
    min_size_m2: 60,
    portals: 'Facebook',
    max_leads_per_portal: 10,
    facebook_groups: []
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showFBModal, setShowFBModal] = useState(false)
  const [newGroup, setNewGroup] = useState('')

  const AVAILABLE_PORTALS = ['Fotocasa', 'Habitaclia', 'Pisos.com', 'Facebook', 'Catastro']

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    setLoading(true)
    const { data } = await insforge.database
      .from('user_settings')
      .select('*')
      .limit(1)
      .single()
    
    if (data) setSettings({
        ...data,
        cities: data.cities || [],
        facebook_groups: data.facebook_groups || []
    })
    setLoading(false)
  }

  const handleSave = async () => {
    setSaving(true)
    const { error } = await insforge.database
      .from('user_settings')
      .upsert({
        ...settings,
        updated_at: new Date().toISOString()
      })
    
    if (!error) {
      console.log('Settings saved')
    }
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

  const handleManualUpdate = async () => {
    setSaving(true)
    await handleSave()
    
    const { error } = await insforge.database
      .from('scraping_requests')
      .insert({
        status: 'pending',
        requested_at: new Date().toISOString(),
        source_name: 'Manual Trigger'
      })

    if (!error) {
      alert('🚀 ¡Misión lanzada! El radar está escaneando los grupos.')
    }
    setSaving(false)
  }

  if (loading) return <div className="p-12 text-slate-400 font-medium">Cargando radar...</div>

  return (
    <div className="p-8 lg:p-12 max-w-2xl animate-in fade-in duration-500 pb-32">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-12">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Configuración</h1>
          <p className="text-slate-400 text-sm mt-2 font-medium">Controla las fuentes y filtros de inteligencia</p>
        </div>
        <button 
          onClick={handleManualUpdate}
          disabled={saving}
          className="w-full sm:w-auto bg-emerald-500 hover:bg-emerald-600 text-white px-8 py-4 rounded-2xl flex items-center justify-center gap-3 text-xs font-black uppercase tracking-widest transition-all shadow-xl shadow-emerald-500/20 active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={saving ? "animate-spin" : ""} size={18} />
          Actualizar ahora
        </button>
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
            <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Precio Máximo (€)</label>
            <input 
              type="number" 
              value={settings.max_price} 
              onChange={(e) => setSettings({...settings, max_price: parseInt(e.target.value)})}
              className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-[0.2em] font-black text-slate-400 mb-3">Cuota de Oportunidades</label>
            <input 
              type="number" 
              value={settings.max_leads_per_portal || 10} 
              onChange={(e) => setSettings({...settings, max_leads_per_portal: parseInt(e.target.value)})}
              className="w-full px-6 py-4 bg-slate-50 rounded-2xl border-2 border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-black text-blue-600"
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
                  <Facebook size={20} fill="currentColor" />
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
                {settings.facebook_groups.map(id => (
                  <div key={id} className="bg-white border border-slate-100 px-4 py-2 rounded-xl flex items-center gap-3 shadow-sm group hover:border-blue-200 transition-all animate-in zoom-in-90">
                    <div className="flex flex-col">
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">ID: {id}</span>
                      <span className="text-xs font-black text-slate-700">facebook.com/groups/...</span>
                    </div>
                    <button 
                      onClick={() => removeGroup(id)}
                      className="text-slate-300 hover:text-red-500 transition-all"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
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
