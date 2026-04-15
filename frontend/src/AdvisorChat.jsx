import { useState, useRef, useEffect } from 'react'
import { MessageSquare, Send, X, Bot, User, Trash2, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'https://esm.sh/react-markdown@9.0.1'

export default function AdvisorChat({ insforge }) {
  const [isOpen, setIsOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: '¡Hola! Soy tu Asesor de HolanducIA. Puedo realizar comparativas, valoraciones y rankings con los datos actuales del mercado. ¿En qué puedo ayudarte hoy?' }
  ])
  const [isTyping, setIsTyping] = useState(false)
  const chatEndRef = useRef(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatHistory])

  const handleSend = async () => {
    if (!message.trim()) return

    const userMessage = { role: 'user', content: message }
    setChatHistory(prev => [...prev, userMessage])
    setMessage('')
    setIsTyping(true)

    try {
      // Fix: Resolve functions URL correctly (stripping regional subdomains like .eu-central)
      const baseUrl = import.meta.env.VITE_INSFORGE_URL
      const functionsUrl = baseUrl.replace(/(\/\/\w+)\..*/, '$1.functions.insforge.app')
      
      const response = await fetch(`${functionsUrl}/advisor-chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${import.meta.env.VITE_INSFORGE_ANON_KEY}`
        },
        body: JSON.stringify({
          message: message,
          previousMessages: chatHistory.slice(-6)
        })
      })

      const data = await response.json()
      if (data.response) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: data.response }])
      } else {
        throw new Error(data.error || 'Error desconocido')
      }
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${err.message}` }])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <>
      {/* Floating Button */}
      <motion.button
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        className="fixed bottom-8 right-8 w-16 h-16 bg-[#00acee] text-white rounded-full shadow-2xl flex items-center justify-center z-[100] hover:bg-[#0072b1] transition-colors"
      >
        <MessageSquare size={28} />
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 100, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 100, scale: 0.9 }}
            className="fixed bottom-28 right-8 w-[95vw] sm:w-[400px] h-[600px] bg-white rounded-3xl shadow-2xl border border-slate-100 flex flex-col z-[100] overflow-hidden"
          >
            {/* Header */}
            <div className="bg-[#0f172a] p-6 flex items-center justify-between text-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#00acee] rounded-xl flex items-center justify-center">
                  <Bot size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-sm">Asesor HolanducIA</h3>
                  <p className="text-[10px] text-green-400 font-black uppercase tracking-widest">En línea (Llama 3)</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                 <button onClick={() => setChatHistory([{ role: 'assistant', content: 'Conversación reiniciada.' }])} className="p-2 hover:bg-white/10 rounded-lg text-slate-400">
                    <Trash2 size={18} />
                 </button>
                 <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-white/10 rounded-lg">
                    <X size={24} />
                 </button>
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
              {chatHistory.map((chat, idx) => (
                <div key={idx} className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex gap-3 max-w-[85%] ${chat.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center ${chat.role === 'user' ? 'bg-slate-200' : 'bg-[#00acee] text-white'}`}>
                      {chat.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                    </div>
                    <div className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${chat.role === 'user' ? 'bg-[#0f172a] text-white' : 'bg-white text-slate-700 border border-slate-100'}`}>
                       <ReactMarkdown>{chat.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-100 p-4 rounded-2xl flex items-center gap-2 shadow-sm">
                    <Loader2 size={16} className="animate-spin text-[#00acee]" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Analizando base de datos...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white border-t border-slate-100">
              <div className="relative flex items-center">
                <input 
                  type="text"
                  placeholder="Escribe tu consulta inmobiliaria..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  className="w-full pl-4 pr-12 py-4 bg-slate-100 rounded-2xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[#00acee] transition-all"
                />
                <button 
                  onClick={handleSend}
                  className="absolute right-2 p-2 text-[#00acee] hover:text-[#0072b1] transition-colors"
                >
                  <Send size={20} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
