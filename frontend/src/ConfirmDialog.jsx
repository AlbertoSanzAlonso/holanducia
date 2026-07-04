import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'

export default function ConfirmDialog({ message, onConfirm, onCancel, confirmText = 'Eliminar', cancelText = 'Cancelar', loading = false }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-[200] flex items-center justify-center p-4"
    >
      <div className="absolute inset-0 bg-slate-900/70 backdrop-blur-sm" onClick={onCancel} />
      <motion.div
        initial={{ scale: 0.95, y: 16 }}
        animate={{ scale: 1, y: 0 }}
        className="relative w-full max-w-sm bg-white rounded-[2rem] shadow-2xl p-8 text-center"
      >
        <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertTriangle size={28} className="text-red-500" />
        </div>
        <p className="text-slate-800 font-bold text-lg mb-2">¿Estás seguro?</p>
        <p className="text-slate-500 text-sm mb-8">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-4 rounded-2xl bg-slate-100 text-slate-600 font-black uppercase text-xs tracking-widest hover:bg-slate-200 transition-all"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 py-4 rounded-2xl bg-red-500 text-white font-black uppercase text-xs tracking-widest hover:bg-red-600 transition-all disabled:opacity-50"
          >
            {confirmText}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}
