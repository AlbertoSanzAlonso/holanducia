import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  ShieldCheck, 
  AlertTriangle, 
  Home, 
  Calendar, 
  Maximize2, 
  ExternalLink,
  Map as MapIcon,
  TrendingDown,
  Building2
} from 'lucide-react';

const PropertyIntelligenceModal = ({ property, onClose }) => {
  if (!property) return null;

  const hasDiscrepancy = property.opportunity_reasons?.some(r => r.includes("Discrepancia"));
  const catastroVerified = !!property.catastro_ref;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 lg:p-8"
    >
      <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-md" onClick={onClose} />
      
      <motion.div 
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="relative w-full max-w-5xl bg-white rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col lg:flex-row max-h-[90vh]"
      >
        <button 
          onClick={onClose}
          className="absolute top-6 right-6 z-50 p-3 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-2xl text-white transition-all"
        >
          <X size={24} />
        </button>

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
            <h2 className="text-3xl font-black leading-tight">{property.title}</h2>
            <div className="flex items-center gap-2 mt-2 text-white/80 font-bold uppercase text-xs tracking-widest">
              <MapIcon size={14} className="text-[#00acee]" /> {property.city}
            </div>
          </div>
        </div>

        {/* Intelligence Side */}
        <div className="flex-1 p-8 lg:p-12 overflow-y-auto">
          {/* Header Data */}
          <div className="flex flex-wrap items-center justify-between gap-6 mb-12">
            <div>
              <p className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em] mb-1">Precio de Oferta</p>
              <h3 className="text-4xl font-black text-slate-900">{property.price?.toLocaleString('es-ES')}€</h3>
            </div>
            <div className="flex items-center gap-4">
              <div className={`p-4 rounded-3xl ${catastroVerified ? 'bg-green-50' : 'bg-slate-50'} flex flex-col items-center min-w-[120px]`}>
                <span className={`text-xl font-black ${catastroVerified ? 'text-green-600' : 'text-slate-400'}`}>{property.size_m2}</span>
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
                  {catastroVerified && <span className="text-[9px] font-black bg-green-500 text-white px-2 py-0.5 rounded-full uppercase">Oficial</span>}
               </div>

               {catastroVerified ? (
                 <div className="space-y-4">
                    <div className="flex justify-between items-center text-sm">
                       <span className="text-slate-500 font-medium">Referencia:</span>
                       <span className="text-slate-900 font-bold font-mono">{property.catastro_ref}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                       <span className="text-slate-500 font-medium">Año Construcción:</span>
                       <span className="text-slate-900 font-bold">{property.year_built || '1980'}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                       <span className="text-slate-500 font-medium">Uso Dominante:</span>
                       <span className="text-slate-900 font-bold">Residencial</span>
                    </div>
                 </div>
               ) : (
                 <p className="text-slate-400 text-xs font-medium italic">Pendiente de geolocalización exacta para verificación oficial.</p>
               )}
            </div>

            <div className="p-6 rounded-[2rem] border-2 border-slate-50 bg-slate-50/50">
               <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest flex items-center gap-2 mb-4">
                 <TrendingDown size={16} className="text-[#00acee]" />
                 Análisis de Mercado
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
              <span className="text-sm font-bold text-slate-900">{property.rooms || '-'}</span>
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Habitaciones</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-2xl flex flex-col items-center">
              <Building2 size={18} className="text-slate-400 mb-2" />
              <span className="text-sm font-bold text-slate-900">{property.bathrooms || '-'}</span>
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Baños</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-2xl flex flex-col items-center">
              <Maximize2 size={18} className="text-slate-400 mb-2" />
              <span className="text-sm font-bold text-slate-900">{property.size_m2 || '-'} m²</span>
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Superficie</span>
            </div>
            <div className="p-4 bg-slate-50 rounded-2xl flex flex-col items-center">
              <Home size={18} className="text-slate-400 mb-2" />
              <span className="text-sm font-bold text-slate-900">{property.is_individual ? 'Particular' : 'Profesional'}</span>
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Vendedor</span>
            </div>
          </div>

          {/* AI Insights & Reasons */}
          <div className="mb-12">
             <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest mb-6 flex items-center gap-2">
               <TrendingDown size={16} className="text-[#00acee]" /> Análisis de Oportunidad
             </h4>
             <div className="flex flex-wrap gap-3">
                {property.opportunity_reasons?.map((reason, i) => (
                  <div key={i} className="px-5 py-3 bg-white border border-slate-100 rounded-2xl text-xs font-bold text-slate-700 shadow-sm flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#00acee]" />
                    {reason}
                  </div>
                ))}
             </div>
          </div>

          {/* Full Description */}
          <div className="mb-12">
             <h4 className="text-slate-900 font-black text-xs uppercase tracking-widest mb-4 flex items-center gap-2">
               Información Detallada
             </h4>
             <p className="text-slate-600 text-sm leading-relaxed bg-slate-50/50 p-6 rounded-3xl border border-slate-50">
                {property.description || "No hay descripción disponible para este inmueble."}
             </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center gap-4 mt-auto pt-6 border-t border-slate-100">
             <a 
              href={property.url} 
              target="_blank" 
              rel="noreferrer"
              className="w-full bg-[#0f172a] text-white py-5 rounded-2xl font-black uppercase text-xs tracking-widest flex items-center justify-center gap-2 hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/20"
             >
               Ver anuncio original <ExternalLink size={14} />
             </a>
             <button className="w-full bg-slate-50 text-slate-900 py-5 rounded-2xl font-black uppercase text-xs tracking-widest border border-slate-200 hover:bg-slate-100 transition-all">
               Guardar en Cartera
             </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default PropertyIntelligenceModal;
