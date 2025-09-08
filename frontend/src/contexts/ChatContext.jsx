import { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { toast } from 'sonner'

const ChatContext = createContext({})

// Use relative URL for production (served from same domain) or localhost for development  
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.MODE === 'production' ? '/api' : 'http://localhost:5001/api')

export function ChatProvider({ children }) {
  const { getAuthHeaders, isAuthenticated } = useAuth()
  const [conversations, setConversations] = useState([])
  const [currentConversation, setCurrentConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [agentCapabilities, setAgentCapabilities] = useState(null)
  const [quickActions, setQuickActions] = useState([])
  const [suggestions, setSuggestions] = useState([])

  // Charger les conversations au démarrage
  useEffect(() => {
    if (isAuthenticated) {
      loadConversations()
      loadAgentCapabilities()
      loadQuickActions()
      loadSuggestions()
    }
  }, [isAuthenticated])

  const loadConversations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations`, {
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        }
      })

      if (response.ok) {
        const data = await response.json()
        setConversations(data.conversations || [])
      }
    } catch (error) {
      console.error('Erreur lors du chargement des conversations:', error)
    }
  }

  const loadAgentCapabilities = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/capabilities`, {
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        }
      })

      if (response.ok) {
        const data = await response.json()
        setAgentCapabilities(data)
      }
    } catch (error) {
      console.error('Erreur lors du chargement des capacités:', error)
    }
  }

  const loadQuickActions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/quick-actions`, {
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        }
      })

      if (response.ok) {
        const data = await response.json()
        setQuickActions(data.quick_actions || [])
      }
    } catch (error) {
      console.error('Erreur lors du chargement des actions rapides:', error)
    }
  }

  const loadSuggestions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/suggestions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        }
      })

      if (response.ok) {
        const data = await response.json()
        setSuggestions(data.suggestions || [])
      } else {
        // Erreur silencieuse - pas de suggestions
        setSuggestions([])
      }
    } catch (error) {
      // Erreur silencieuse - pas de suggestions
      setSuggestions([])
    }
  }

  const createNewConversation = () => {
    setCurrentConversation(null)
    setMessages([])
  }

  const selectConversation = async (conversationId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        }
      })

      if (response.ok) {
        const data = await response.json()
        setCurrentConversation(data.conversation)
        setMessages(data.conversation.messages || [])
      }
    } catch (error) {
      console.error('Erreur lors du chargement de la conversation:', error)
      toast.error('Erreur lors du chargement de la conversation')
    }
  }

  const sendMessage = async (message, businessId = null) => {
    if (!message.trim()) return

    setIsLoading(true)
    setIsTyping(true)

    // Ajouter le message utilisateur immédiatement
    const userMessage = {
      id: Date.now(),
      content: message,
      is_from_user: true,
      created_at: new Date().toISOString(),
      metadata: {}
    }

    setMessages(prev => [...prev, userMessage])

    try {
      const response = await fetch(`${API_BASE_URL}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          message: message,
          conversation_id: currentConversation?.id,
          business_id: businessId
        })
      })

      const data = await response.json()

      if (response.ok) {
        // Ajouter la réponse de l'agent
        const agentMessage = {
          id: data.message_id,
          content: data.response,
          is_from_user: false,
          created_at: data.timestamp,
          metadata: {
            agent_type: data.agent_type,
            capabilities_used: data.capabilities_used,
            success: data.success
          }
        }

        setMessages(prev => [...prev, agentMessage])

        // Mettre à jour la conversation courante
        if (data.conversation_id) {
          setCurrentConversation(prev => ({
            ...prev,
            id: data.conversation_id
          }))
        }

        // Recharger la liste des conversations
        loadConversations()

        return { success: true, data }
      } else {
        toast.error(data.error || 'Erreur lors de l\'envoi du message')
        
        // Supprimer le message utilisateur en cas d'erreur
        setMessages(prev => prev.filter(msg => msg.id !== userMessage.id))
        
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error)
      toast.error('Erreur de connexion au serveur')
      
      // Supprimer le message utilisateur en cas d'erreur
      setMessages(prev => prev.filter(msg => msg.id !== userMessage.id))
      
      return { success: false, error: 'Erreur de connexion au serveur' }
    } finally {
      setIsLoading(false)
      setIsTyping(false)
    }
  }

  const executeQuickAction = async (actionId, businessId = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/agent/execute-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          action_id: actionId,
          business_id: businessId
        })
      })

      const data = await response.json()

      if (response.ok) {
        // Traiter comme un message normal
        const agentMessage = {
          id: data.message_id,
          content: data.response,
          is_from_user: false,
          created_at: data.timestamp,
          metadata: {
            agent_type: data.agent_type,
            capabilities_used: data.capabilities_used,
            success: data.success,
            quick_action: actionId
          }
        }

        setMessages(prev => [...prev, agentMessage])

        // Mettre à jour la conversation courante
        if (data.conversation_id) {
          setCurrentConversation(prev => ({
            ...prev,
            id: data.conversation_id
          }))
        }

        // Recharger la liste des conversations
        loadConversations()

        return { success: true, data }
      } else {
        toast.error(data.error || 'Erreur lors de l\'exécution de l\'action')
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de l\'exécution de l\'action:', error)
      toast.error('Erreur de connexion au serveur')
      return { success: false, error: 'Erreur de connexion au serveur' }
    }
  }

  const deleteConversation = async (conversationId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        }
      })

      if (response.ok) {
        setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        
        if (currentConversation?.id === conversationId) {
          setCurrentConversation(null)
          setMessages([])
        }
        
        toast.success('Conversation supprimée')
        return { success: true }
      } else {
        const data = await response.json()
        toast.error(data.error || 'Erreur lors de la suppression')
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de la suppression:', error)
      toast.error('Erreur de connexion au serveur')
      return { success: false, error: 'Erreur de connexion au serveur' }
    }
  }

  const clearMessages = () => {
    setMessages([])
    setCurrentConversation(null)
  }

  const value = {
    conversations,
    currentConversation,
    messages,
    isLoading,
    isTyping,
    agentCapabilities,
    quickActions,
    suggestions,
    createNewConversation,
    selectConversation,
    sendMessage,
    executeQuickAction,
    deleteConversation,
    clearMessages,
    loadConversations,
    loadSuggestions
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

