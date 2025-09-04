import { createContext, useContext, useState, useEffect } from 'react'
import { toast } from 'sonner'

const AuthContext = createContext({})

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001/api'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [sageConnected, setSageConnected] = useState(false)

  // Vérifier le token au chargement et gérer le retour de Sage
  useEffect(() => {
    const token = localStorage.getItem('token')
    const urlParams = new URLSearchParams(window.location.search)
    const sageAuth = urlParams.get('sage_auth')
    
    // Si on revient de Sage avec succès
    if (sageAuth === 'success') {
      // Nettoyer l'URL
      window.history.replaceState({}, document.title, window.location.pathname)
      
      if (token) {
        // Vérifier la validité du token et mettre à jour le statut Sage
        checkTokenValidityAndSage(token)
      } else {
        setLoading(false)
      }
    } else if (token) {
      // Vérification normale du token
      checkTokenValidity(token)
    } else {
      setLoading(false)
    }
  }, [])

  const checkTokenValidityAndSage = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setIsAuthenticated(true)
        
        // Vérifier le statut Sage et afficher un message de succès
        await checkSageStatus(token)
        toast.success('Connexion à Sage réussie!')
      } else {
        // Token invalide
        localStorage.removeItem('token')
        setIsAuthenticated(false)
        setUser(null)
        toast.error('Session expirée, veuillez vous reconnecter')
      }
    } catch (error) {
      console.error('Erreur lors de la vérification du token:', error)
      localStorage.removeItem('token')
      setIsAuthenticated(false)
      setUser(null)
      toast.error('Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const checkTokenValidity = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setIsAuthenticated(true)
        
        // Vérifier le statut Sage
        checkSageStatus(token)
      } else {
        // Token invalide
        localStorage.removeItem('token')
        setIsAuthenticated(false)
        setUser(null)
      }
    } catch (error) {
      console.error('Erreur lors de la vérification du token:', error)
      localStorage.removeItem('token')
      setIsAuthenticated(false)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const checkSageStatus = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/sage/status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        setSageConnected(data.authenticated)
      } else {
        // Erreur silencieuse - pas de Sage connecté
        setSageConnected(false)
      }
    } catch (error) {
      // Erreur silencieuse - pas de Sage connecté
      setSageConnected(false)
    }
  }

  const login = async (email, password) => {
    try {
      setLoading(true)
      
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()

      if (response.ok) {
        localStorage.setItem('token', data.access_token)
        setUser(data.user)
        setIsAuthenticated(true)
        
        // Vérifier le statut Sage
        checkSageStatus(data.access_token)
        
        toast.success('Connexion réussie!')
        return { success: true }
      } else {
        toast.error(data.error || 'Erreur lors de la connexion')
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de la connexion:', error)
      toast.error('Erreur de connexion au serveur')
      return { success: false, error: 'Erreur de connexion au serveur' }
    } finally {
      setLoading(false)
    }
  }

  const register = async (username, email, password) => {
    try {
      setLoading(true)
      
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, email, password })
      })

      const data = await response.json()

      if (response.ok) {
        toast.success('Inscription réussie! Vous pouvez maintenant vous connecter.')
        return { success: true }
      } else {
        toast.error(data.error || 'Erreur lors de l\'inscription')
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de l\'inscription:', error)
      toast.error('Erreur de connexion au serveur')
      return { success: false, error: 'Erreur de connexion au serveur' }
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    setIsAuthenticated(false)
    setSageConnected(false)
    toast.success('Déconnexion réussie')
  }

  const connectSage = async (country = null) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        toast.error('Vous devez être connecté')
        return { success: false }
      }

      const response = await fetch(`${API_BASE_URL}/sage/auth/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          scope: 'full_access',
          country: country 
        })
      })

      const data = await response.json()

      if (response.ok) {
        // Rediriger vers l'URL d'autorisation Sage dans le même onglet
        window.location.href = data.authorization_url
        return { success: true }
      } else {
        toast.error(data.error || 'Erreur lors de la connexion à Sage')
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de la connexion à Sage:', error)
      toast.error('Erreur de connexion au serveur')
      return { success: false, error: 'Erreur de connexion au serveur' }
    }
  }

  const disconnectSage = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return

      const response = await fetch(`${API_BASE_URL}/sage/disconnect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        setSageConnected(false)
        toast.success('Déconnexion de Sage réussie')
        return { success: true }
      } else {
        const data = await response.json()
        toast.error(data.error || 'Erreur lors de la déconnexion de Sage')
        return { success: false, error: data.error }
      }
    } catch (error) {
      console.error('Erreur lors de la déconnexion de Sage:', error)
      toast.error('Erreur de connexion au serveur')
      return { success: false, error: 'Erreur de connexion au serveur' }
    }
  }

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token')
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }

  const value = {
    user,
    isAuthenticated,
    loading,
    sageConnected,
    login,
    register,
    logout,
    connectSage,
    disconnectSage,
    checkSageStatus: () => checkSageStatus(localStorage.getItem('token')),
    getAuthHeaders
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

