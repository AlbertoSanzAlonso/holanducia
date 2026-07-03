import { useState, useRef, useEffect } from 'react'
import { MessageSquare, Send, X, Bot, User, Trash2, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'https://esm.sh/react-markdown@9.0.1'

export default function AdvisorChat() {
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

    // TODO: endpoint FastAPI /api/advisor/chat en el VPS
    setChatHistory(prev => [...prev, {
      role: 'assistant',
      content: 'El chat asesor se migrará a la API del VPS. Por ahora usa el dashboard para gestionar oportunidades.'
    }])
    setIsTyping(false)
  }

  return (