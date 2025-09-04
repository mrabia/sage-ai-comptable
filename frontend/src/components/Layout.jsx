import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { 
  Bot, 
  MessageSquare, 
  Settings, 
  LogOut, 
  User, 
  Menu,
  X,
  Link as LinkIcon,
  Unlink
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useChat } from '@/contexts/ChatContext'

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout, sageConnected, connectSage } = useAuth()
  const { conversations, createNewConversation, selectConversation, currentConversation } = useChat()
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleNewChat = () => {
    createNewConversation()
    setSidebarOpen(false)
  }

  const handleSelectConversation = (conversation) => {
    selectConversation(conversation.id)
    setSidebarOpen(false)
  }

  const navigation = [
    { name: 'Chat', href: '/chat', icon: MessageSquare, current: location.pathname === '/chat' },
    { name: 'Paramètres', href: '/settings', icon: Settings, current: location.pathname === '/settings' }
  ]

  return (
    <div className="h-screen flex bg-gray-50 dark:bg-gray-900">
      {/* Sidebar mobile backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="absolute inset-0 bg-gray-600 opacity-75"></div>
        </div>
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-80 bg-white dark:bg-gray-800 shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary rounded-lg">
                <Bot className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Sage AI
                </h1>
                <div className="flex items-center space-x-2">
                  {sageConnected ? (
                    <Badge variant="success" className="text-xs">
                      <LinkIcon className="h-3 w-3 mr-1" />
                      Sage connecté
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">
                      <Unlink className="h-3 w-3 mr-1" />
                      Sage déconnecté
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Nouveau chat */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <Button 
              onClick={handleNewChat}
              className="w-full justify-start"
              variant="outline"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Nouvelle conversation
            </Button>
          </div>

          {/* Connexion Sage */}
          {!sageConnected && (
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <Button 
                onClick={() => connectSage()}
                className="w-full justify-start"
                variant="default"
              >
                <LinkIcon className="h-4 w-4 mr-2" />
                Connecter Sage
              </Button>
            </div>
          )}

          {/* Liste des conversations */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
                Conversations récentes
              </h3>
              {conversations.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  Aucune conversation
                </p>
              ) : (
                conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => handleSelectConversation(conversation)}
                    className={`
                      w-full text-left p-3 rounded-lg transition-colors
                      ${currentConversation?.id === conversation.id 
                        ? 'bg-primary/10 border border-primary/20' 
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }
                    `}
                  >
                    <div className="truncate text-sm font-medium text-gray-900 dark:text-white">
                      {conversation.title || 'Nouvelle conversation'}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {new Date(conversation.updated_at).toLocaleDateString('fr-FR')}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Navigation */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <nav className="space-y-2">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors
                    ${item.current
                      ? 'bg-primary text-primary-foreground'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }
                  `}
                >
                  <item.icon className="h-4 w-4 mr-3" />
                  {item.name}
                </Link>
              ))}
            </nav>
          </div>

          {/* User menu */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="w-full justify-start p-2">
                  <Avatar className="h-8 w-8 mr-3">
                    <AvatarImage src={user?.avatar} />
                    <AvatarFallback>
                      {user?.username?.charAt(0).toUpperCase() || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="text-left">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {user?.username || 'Utilisateur'}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {user?.email}
                    </div>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>Mon compte</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/settings')}>
                  <User className="mr-2 h-4 w-4" />
                  Profil
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/settings')}>
                  <Settings className="mr-2 h-4 w-4" />
                  Paramètres
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Se déconnecter
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar mobile */}
        <div className="lg:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="flex items-center space-x-2">
              <Bot className="h-6 w-6 text-primary" />
              <span className="font-semibold text-gray-900 dark:text-white">Sage AI</span>
            </div>
            <div className="w-10"></div> {/* Spacer for centering */}
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  )
}

