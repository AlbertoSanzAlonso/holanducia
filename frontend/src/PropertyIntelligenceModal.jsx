import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  X, ShieldCheck, AlertTriangle, Home, Calendar, Maximize2, 
  ExternalLink, Map as MapIcon, TrendingDown, Building2,
  Trash2, Edit3, Save, RotateCcw
} from 'lucide-react';

const PropertyIntelligenceModal = ({ property: initialProperty, categories, onClose, onUpdate, onDelete }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [property, setProperty] = useState(initialProperty);
  const [saving, setSaving] = useState(false);

  if (!property) return null;

  const hasDiscrepancy = property.opportunity_reasons?.some(r => r.includes("Discrepancia"));
  const catastroVerified = !!property.catastro_ref;

  const handleSave = async () => {
    setSaving(true);
    await onUpdate(property);
    setIsEditing(false);
    setSaving(false);
  };

  const handleDelete = async () => {
    if (window.confirm('¿Estás seguro de que quieres eliminar esta propiedad de la base de datos?')) {
      await onDelete(property.id);
      onClose();
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 lg:p-12"
    >
      <div className="absolute inset-0 bg-slate-900/90 backdrop-blur-xl" onClick={onClose} />
      
      <motion.div 
        initial={{ scale: 0.9, y: 30 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 30 }}
        className="relative w-full max-w-6xl bg-white rounded-[3rem] shadow-[0_50px_100px_rgba(0,0,0,0.4)] overflow-hidden flex flex-col lg:flex-row max-h-[90vh]"
      >
        {/* Toolbar Superior - Ahora flotando con contraste real */}
        <div className="absolute top-8 right-8 z-[110] flex gap-3">
            {!isEditing ? (
                <button 
                    onClick={() => setIsEditing(true)}
                    className="p-4 bg-slate-900 hover:bg-black rounded-2xl text-white transition-all shadow-2xl hover:scale-105 active:scale-95"
                >
                    <Edit3 size={22} />
                </button>
            ) : (
                <button 
                    onClick={handleSave}
                    disabled={saving}
                    className="p-4 bg-emerald-500 hover:bg-emerald-600 rounded-2xl text-white transition-all shadow-2xl hover:scale-105 active:scale-95"
                >
                    <Save size={22} />
                </button>
            )}
            <button 
                onClick={handleDelete}
                className="p-4 bg-red-500 hover:bg-red-600 rounded-2xl text-white transition-all shadow-2xl hover:scale-105 active:scale-95"
            >
                <Trash2 size={22} />
            </button>
            <div className="w-px bg-slate-200 h-10 mx-2 self-center" />
            <button 
                onClick={onClose}
                className="p-4 bg-slate-100 hover:bg-slate-200 rounded-2xl text-slate-900 transition-all shadow-xl hover:scale-105 active:scale-95"
            >
                <X size={22} />
            </button>
        </div>

        {/* Media Side */}
        <div className="lg:w-2/5 relative h-64 lg:h-auto bg-slate-100">
          <img 
            src={property.images?.[0] || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000&auto=format&fit=crop'} 
            className="w-full h-full object-cover"
            alt={property.title}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent opacity-60" />
          
          <div className="absolute bottom-8 left-8 right-8 text-white">
            <span className="px-3 py-1.5 bg-[#00acee] rounded-full text-[10px] font-black uppercase tracking-wider mb-4 inline-block shadow-lg">
              {property.source}
            </span>
            {isEditing ? (
                <input 
                    className="bg-white/20 border border-white/30 rounded-xl px-3 py-2 text-xl font-bold w-full text-white outline-none focus:bg-white/30 transition-all"
                    value={property.title}
                    onChange={(e) => setProperty({...property, title: e.target.value})}
                />
            ) : (
                <h2 className="text-3xl font-black leading-tight">{property.title}</h2>
            )}
            <div className="flex items-center gap-2 mt-2 text-white/80 font-bold uppercase text-xs tracking-widest">
              <MapIcon size={14} className="text-[#00acee]" /> 
              {isEditing ? (
                  <input 
                    className="bg-transparent border-b border-white/20 text-white outline-none w-32"
                    value={property.city}
                    onChange={(e) => setProperty({...property, city: e.target.value})}
                  />
              ) : property.city}
            </div>
          </div>
        </div>

        {/* Intelligence Side */}
        <div className="flex-1 p-8 lg:p-12 overflow-y-auto">
          {/* Header Data */}
          <div className="flex flex-wrap items-center justify-between gap-6 mb-12">
            <div>
              <p className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em] mb-1">Precio de Oferta</p>
              {isEditing ? (
                  <div className="flex items-center gap-2">
                    <input 
                        type="number"
                        className="text-3xl font-black text-slate-900 bg-slate-50 border-b-2 border-[#00acee] w-48 outline-none"
                        value={property.price}
                        onChange={(e) => setProperty({...property, price: parseInt(e.target.value)})}
                    />
                    <span className="text-2xl font-black text-slate-900">€</span>
                  </div>
              ) : (
                <h3 className="text-4xl font-black text-slate-900">{property.price?.toLocaleString('es-ES')}€</h3>
              )}
            </div>
            <div className="flex items-center gap-4">
              <div className={`p-4 rounded-3xl ${catastroVerified ? 'bg-green-50' : 'bg-slate-50'} flex flex-col items-center min-w-[120px]`}>
                {isEditing ? (
                    <input 
                        type="number"
                        className="text-xl font-black text-[#00acee] bg-transparent text-center w-16 outline-none"
                        value={property.size_m2}
                        onChange={(e) => setProperty({...property, size_m2: parseInt(e.target.value)})}
                    />
                ) : (
                    <span className={`text-xl font-black ${catastroVerified ? 'text-green-600' : 'text-slate-400'}`}>{property.size_m2}</span>
                )}
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">m² Totales</span>
              </div>
              <div className="p-4 bg-orange-50 rounded-3xl flex flex-col items-center min-w-[120px]">
                <span className="text-xl font-black text-orange-600">{property.opportunity_score}</span>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Score IA</span>
              </div>
            </div>
          </div>

          {/* Triangulation Logic */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            <div className={`p-6 rounded-[2rem] border-2 ${hasDiscrepancy ? 'border-orange-100 bg-orange-50/30' : 'border-slate-50 bg-slate-50/50'}`}>
               <div className="flex items-center justify-between mb-4">
                  <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest flex items-center gap-2">
                    {catastroVerified ? <ShieldCheck size={16} className="text-green-500" /> : <AlertTriangle size={16} className="text-orange-500" />}
                    Datos Catastrales
                  </h4>
               </div>

               <div className="space-y-4">
                    <div className="flex justify-between items-center text-sm">
                       <span className="text-slate-500 font-medium">Referencia:</span>
                       {isEditing ? (
                           <input 
                            className="text-slate-900 font-bold font-mono bg-white border rounded px-2"
                            value={property.catastro_ref || ''}
                            onChange={(e) => setProperty({...property, catastro_ref: e.target.value})}
                           />
                       ) : (
                           <span className="text-slate-900 font-bold font-mono">{property.catastro_ref || 'NO DISPONIBLE'}</span>
                       )}
                    </div>
                    <div className="flex justify-between items-center text-sm">
                       <span className="text-slate-500 font-medium">Año Construcción:</span>
                       <span className="text-slate-900 font-bold">{property.year_built || '1980'}</span>
                    </div>
               </div>
            </div>

            <div className="p-6 rounded-[2rem] border-2 border-slate-50 bg-slate-50/50">
               <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest flex items-center gap-2 mb-4">
                 <TrendingDown size={16} className="text-[#00acee]" /> Análisis de Mercado
               </h4>
               <div className="space-y-4">
                  <div className="flex justify-between items-center text-sm">
                     <span className="text-slate-500 font-medium">Precio m² (Anuncio):</span>
                     <span className="text-slate-900 font-bold">{Math.round(property.price / (property.size_m2 || 1))}€</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                     <span className="text-slate-500 font-medium">Media de Zona:</span>
                     <span className="text-slate-900 font-bold">3.200€</span>
                  </div>
               </div>
            </div>
          </div>

          {/* Features */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            <div className="p-4 bg-slate-50 rounded-2xl flex flex-col items-center">
              <Calendar size={18} className="text-slate-400 mb-2" />
              {isEditing ? (
                  <input type="number" className="w-12 text-center bg-transparent border-b font-bold" value={property.rooms || 0} onChange={(e) => setProperty({...property, rooms: parseInt(e.target.value)})}/>
              ) : (
                  <span className="text-sm font-bold text-slate-900">{property.rooms || '-'}</span>
              )}
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Habitaciones</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-2xl flex flex-col items-center">
              <Building2 size={18} className="text-slate-400 mb-2" />
              {isEditing ? (
                  <input type="number" className="w-12 text-center bg-transparent border-b font-bold" value={property.bathrooms || 0} onChange={(e) => setProperty({...property, bathrooms: parseInt(e.target.value)})}/>
              ) : (
                  <span className="text-sm font-bold text-slate-900">{property.bathrooms || '-'}</span>
              )}
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Baños</span>
            </div>
            {/* ... más features ... */}
          </div>

          {/* Full Description */}
          <div className="mb-12">
             <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest mb-4 flex items-center gap-2">
               Información Detallada
             </h4>
             {isEditing ? (
                 <textarea 
                    className="w-full h-48 p-6 rounded-3xl border border-slate-200 bg-slate-50 outline-none focus:bg-white transition-all text-sm leading-relaxed"
                    value={property.description}
                    onChange={(e) => setProperty({...property, description: e.target.value})}
                 />
             ) : (
                 <p className="text-slate-600 text-sm leading-relaxed bg-slate-50/50 p-6 rounded-3xl border border-slate-50">
                    {property.description || "No hay descripción disponible."}
                 </p>
             )}
          </div>

          {/* Category Selector */}
          <div className="mb-12">
             <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest mb-4 flex items-center gap-2">
               📂 Categoría en Cartera
             </h4>
             <div className="flex flex-wrap gap-2">
                {categories?.map(cat => (
                    <button 
                        key={cat.id}
                        onClick={() => onUpdate({...property, category_id: cat.id})}
                        className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all border-2 ${property.category_id === cat.id ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-100 text-slate-400 hover:border-slate-200'}`}
                    >
                        {cat.name}
                    </button>
                ))}
             </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center gap-4 mt-auto pt-6 border-t border-slate-100">
             <a 
              href={property.url} target="_blank" rel="noreferrer"
              className="w-full bg-[#0f172a] text-white py-5 rounded-2xl font-black uppercase text-xs tracking-widest flex items-center justify-center gap-2 hover:bg-slate-800 transition-all shadow-xl"
             >
               Ver anuncio original <ExternalLink size={14} />
             </a>
             {isEditing && (
                 <button onClick={() => { setProperty(initialProperty); setIsEditing(false); }} className="w-full bg-slate-100 text-slate-500 py-5 rounded-2xl font-black uppercase text-xs tracking-widest flex items-center justify-center gap-2">
                   <RotateCcw size={14} /> Cancelar cambios
                 </button>
             )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default PropertyIntelligenceModal;
