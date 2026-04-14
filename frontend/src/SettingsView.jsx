import { useState, useEffect } from 'react'
import { Save, RefreshCw } from 'lucide-react'

export default function SettingsView({ insforge }) {
  const [settings, setSettings] = useState({
    cities: ['madrid', 'barcelona'],
    max_price: 300000,
    min_rooms: 2,
    min_size_m2: 60
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    setLoading(true)
    const { data, error } = await insforge.database
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
      alert('Configuración guardada correctamente. Los scrapers usarán estos filtros en la próxima ejecución.')
    }
    setSaving(false)
  }

  if (loading) return <div className="p-12 text-slate-400">Cargando configuración...</div>

  return (
    <div className="p-12 max-w-2xl">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Configuración del Radar</h1>
      
      <div className="space-y-6 bg-white p-8 rounded-2xl border border-slate-100 shadow-sm">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">Ciudades (separadas por coma)</label>
          <input 
            type="text" 
            value={settings.cities.join(', ')} 
            onChange={(e) => setSettings({...settings, cities: e.target.value.split(',').map(s => s.trim())})}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#00acee] transition-all"
          />
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Precio Máximo (€)</label>
            <input 
              type="number" 
              value={settings.max_price} 
              onChange={(e) => setSettings({...settings, max_price: parseInt(e.target.value)})}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#00acee]"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Habitaciones mín.</label>
            <input 
              type="number" 
              value={settings.min_rooms} 
              onChange={(e) => setSettings({...settings, min_rooms: parseInt(e.target.value)})}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#00acee]"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">Superficie mín. (m²)</label>
          <input 
            type="number" 
            value={settings.min_size_m2} 
            onChange={(e) => setSettings({...settings, min_size_m2: parseInt(e.target.value)})}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#00acee]"
          />
        </div>

        <button 
          onClick={handleSave}
          disabled={saving}
          className="w-full mt-4 bg-[#00acee] hover:bg-[#009bd6] text-white font-bold py-4 rounded-xl shadow-lg shadow-[#00acee30] flex items-center justify-center gap-2 transition-all disabled:opacity-50"
        >
          {saving ? <RefreshCw className="animate-spin" size={20} /> : <Save size={20} />}
          Guardar Configuración
        </button>
      </div>

      <div className="mt-8 p-6 bg-blue-50 rounded-xl border border-blue-100">
        <p className="text-sm text-blue-700">
          <strong>Tip:</strong> Cuanto más específicos sean los filtros, mayores probabilidades de encontrar "Flash Opportunities" reales sin ruido.
        </p>
      </div>
    </div>
  )
}
