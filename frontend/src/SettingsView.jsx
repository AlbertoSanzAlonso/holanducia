import { useState, useEffect } from 'react'
import { Save, RefreshCw } from 'lucide-react'

export default function SettingsView({ insforge }) {
  const [settings, setSettings] = useState({
    cities: ['madrid', 'barcelona'],
    max_price: 300000,
    min_rooms: 2,
    min_size_m2: 60,
    portals: 'Fotocasa, Habitaclia, Pisos.com',
    max_leads_per_portal: 10
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

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
        cities: data.cities || ['madrid', 'barcelona']
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
      alert('🚀 ¡Misión lanzada! El servidor está empezando a recopilar información.')
    } else {
      alert('Error: ' + error.message)
    }
    setSaving(false)
  }

  if (loading) return <div className="p-12 text-slate-400 font-medium">Cargando radar...</div>

  return (
    <div className="p-12 max-w-2xl animate-in fade-in duration-500">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Configuración</h1>
          <p className="text-slate-500 text-sm mt-1">Controla las fuentes y filtros de inteligencia</p>
        </div>
        <button 
          onClick={handleManualUpdate}
          disabled={saving}
          className="bg-emerald-500 hover:bg-emerald-600 text-white px-5 py-2.5 rounded-xl flex items-center gap-2 text-sm font-bold transition-all shadow-lg shadow-emerald-200 active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={saving ? "animate-spin" : ""} size={18} />
          Actualizar ahora
        </button>
      </div>
      
      <div className="space-y-6 bg-white p-8 rounded-3xl border border-slate-100 shadow-xl shadow-slate-200/50">
        <div>
          <label className="block text-xs uppercase tracking-wider font-bold text-slate-400 mb-2">Ciudades de rastreo</label>
          <input 
            type="text" 
            placeholder="Ej: malaga, benalmadena (dejar vacío para rastrear todo)"
            value={(settings.cities || []).join(', ')} 
            onChange={(e) => setSettings({...settings, cities: e.target.value ? e.target.value.split(',').map(s => s.trim()) : []})}
            className="w-full px-4 py-3 bg-slate-100 rounded-xl border border-transparent focus:border-[#00acee] focus:bg-white focus:ring-4 focus:ring-blue-50 outline-none transition-all font-medium"
          />
        </div>

        <div>
          <label className="block text-xs uppercase tracking-wider font-bold text-slate-400 mb-3">Fuentes de Datos (Portales)</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {AVAILABLE_PORTALS.map(portal => (
              <label 
                key={portal}
                className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all ${
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
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-xs uppercase tracking-wider font-bold text-slate-400 mb-2">Precio Máximo (€)</label>
            <input 
              type="number" 
              value={settings.max_price} 
              onChange={(e) => setSettings({...settings, max_price: parseInt(e.target.value)})}
              className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wider font-bold text-slate-400 mb-2">Límite de rascado</label>
            <input 
              type="number" 
              placeholder="Ej: 5"
              value={settings.max_leads_per_portal || 10} 
              onChange={(e) => setSettings({...settings, max_leads_per_portal: parseInt(e.target.value)})}
              className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold text-blue-600"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-xs uppercase tracking-wider font-bold text-slate-400 mb-2">Habitaciones mín.</label>
            <input 
              type="number" 
              value={settings.min_rooms} 
              onChange={(e) => setSettings({...settings, min_rooms: parseInt(e.target.value)})}
              className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold"
            />
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wider font-bold text-slate-400 mb-2">Superficie mín. (m²)</label>
            <input 
              type="number" 
              value={settings.min_size_m2} 
              onChange={(e) => setSettings({...settings, min_size_m2: parseInt(e.target.value)})}
              className="w-full px-4 py-3 bg-slate-50 rounded-xl border border-transparent focus:border-[#00acee] focus:bg-white outline-none transition-all font-bold"
            />
          </div>
        </div>

        <button 
          onClick={handleSave}
          disabled={saving}
          className="w-full mt-4 bg-slate-900 hover:bg-black text-white font-bold py-4 rounded-2xl shadow-xl shadow-slate-900/20 flex items-center justify-center gap-2 transition-all active:scale-[0.98] disabled:opacity-50"
        >
          {saving ? <RefreshCw className="animate-spin" size={20} /> : <Save size={20} />}
          Guardar Filtros
        </button>
      </div>

    </div>
  )
}
