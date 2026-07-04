import { useState } from 'react'
import { motion } from 'framer-motion'
import { Save, Trash2, X } from 'lucide-react'
import { LIST_COLORS } from './utils/listColors'

export default function ListEditModal({ list, onClose, onSave, onDelete }) {
  const isEdit = Boolean(list?.id)
  const [name, setName] = useState(list?.name || '')
  const [description, setDescription] = useState(list?.description || '')
  const [color, setColor] = useState(list?.color || LIST_COLORS[0])
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    try {
      await onSave({ name: name.trim(), description: description.trim() || null, color })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit || !window.confirm(`¿Eliminar la lista "${list.name}"? Las propiedades no se borran.`)) return
    setSaving(true)
    try {
      await onDelete(list.id)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[120] flex items-center justify-center p-4"
    >
      <div className="absolute inset-0 bg-slate-900/70 backdrop-blur-sm" onClick={onClose} />
      <motion.form
        initial={{ scale: 0.95, y: 16 }}
        animate={{ scale: 1, y: 0 }}
        onSubmit={handleSubmit}
        className="relative w-full max-w-md bg-white rounded-[2rem] shadow-2xl p-8"
      >
        <div className="flex items-center justify-between mb-8">
          <h3 className="text-xl font-black text-slate-900">
            {isEdit ? 'Editar lista' : 'Nueva lista'}
          </h3>
          <button type="button" onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 text-slate-400">
            <X size={20} />
          </button>
        </div>

        <label className="block mb-4">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Nombre</span>
          <input
            required
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej. Favoritos Málaga centro"
            className="w-full px-4 py-3 rounded-xl border border-slate-200 font-semibold outline-none focus:border-[#00acee] focus:ring-2 focus:ring-[#00acee]/20"
          />
        </label>

        <label className="block mb-4">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Descripción (opcional)</span>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Notas sobre esta selección..."
            className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm outline-none focus:border-[#00acee] resize-none"
          />
        </label>

        <div className="mb-8">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3 block">Color</span>
          <div className="flex flex-wrap gap-2">
            {LIST_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                style={{ backgroundColor: c }}
                className={`w-9 h-9 rounded-xl transition-transform ${color === c ? 'ring-2 ring-offset-2 ring-slate-900 scale-110' : 'hover:scale-105'}`}
              />
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          {isEdit && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={saving}
              className="p-4 rounded-2xl bg-red-50 text-red-500 hover:bg-red-500 hover:text-white transition-colors"
            >
              <Trash2 size={20} />
            </button>
          )}
          <button
            type="submit"
            disabled={saving || !name.trim()}
            className="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl bg-[#0f172a] text-white font-black uppercase text-xs tracking-widest hover:bg-slate-800 disabled:opacity-50"
          >
            <Save size={16} />
            {isEdit ? 'Guardar' : 'Crear lista'}
          </button>
        </div>
      </motion.form>
    </motion.div>
  )
}
