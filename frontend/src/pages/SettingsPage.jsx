import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { 
  User, 
  Link as LinkIcon, 
  Unlink, 
  Shield, 
  Bell, 
  Palette,
  Trash2,
  Save,
  AlertTriangle
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/components/theme-provider'
import { toast } from 'sonner'

export default function SettingsPage() {
  const { user, sageConnected, connectSage, disconnectSage, checkSageStatus } = useAuth()
  const { theme, setTheme } = useTheme()
  
  const [profileData, setProfileData] = useState({
    username: user?.username || '',
    email: user?.email || ''
  })
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [notifications, setNotifications] = useState({
    emailNotifications: true,
    pushNotifications: false,
    weeklyReports: true
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) {
      setProfileData({
        username: user.username || '',
        email: user.email || ''
      })
    }
  }, [user])

  const handleProfileUpdate = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      // Simuler l'appel API
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success('Profil mis à jour avec succès')
    } catch (error) {
      toast.error('Erreur lors de la mise à jour du profil')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordUpdate = async (e) => {
    e.preventDefault()
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('Les mots de passe ne correspondent pas')
      return
    }

    if (passwordData.newPassword.length < 6) {
      toast.error('Le mot de passe doit contenir au moins 6 caractères')
      return
    }

    setLoading(true)

    try {
      // Simuler l'appel API
      await new Promise(resolve => setTimeout(resolve, 1000))
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      toast.success('Mot de passe mis à jour avec succès')
    } catch (error) {
      toast.error('Erreur lors de la mise à jour du mot de passe')
    } finally {
      setLoading(false)
    }
  }

  const handleSageConnection = async () => {
    if (sageConnected) {
      const result = await disconnectSage()
      if (result.success) {
        checkSageStatus()
      }
    } else {
      await connectSage()
    }
  }

  const handleNotificationChange = (key, value) => {
    setNotifications(prev => ({
      ...prev,
      [key]: value
    }))
    toast.success('Préférences de notification mises à jour')
  }

  const handleDeleteAccount = async () => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer votre compte ? Cette action est irréversible.')) {
      try {
        // Simuler l'appel API
        await new Promise(resolve => setTimeout(resolve, 1000))
        toast.success('Compte supprimé avec succès')
      } catch (error) {
        toast.error('Erreur lors de la suppression du compte')
      }
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Paramètres
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Gérez votre compte et vos préférences
          </p>
        </div>

        {/* Profil utilisateur */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <User className="h-5 w-5" />
              <span>Profil utilisateur</span>
            </CardTitle>
            <CardDescription>
              Modifiez vos informations personnelles
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleProfileUpdate} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Nom d'utilisateur</Label>
                  <Input
                    id="username"
                    value={profileData.username}
                    onChange={(e) => setProfileData(prev => ({
                      ...prev,
                      username: e.target.value
                    }))}
                    disabled={loading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={profileData.email}
                    onChange={(e) => setProfileData(prev => ({
                      ...prev,
                      email: e.target.value
                    }))}
                    disabled={loading}
                  />
                </div>
              </div>
              <Button type="submit" disabled={loading}>
                <Save className="h-4 w-4 mr-2" />
                Sauvegarder
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Connexion Sage */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              {sageConnected ? (
                <LinkIcon className="h-5 w-5 text-green-600" />
              ) : (
                <Unlink className="h-5 w-5 text-gray-400" />
              )}
              <span>Connexion Sage Business Cloud</span>
            </CardTitle>
            <CardDescription>
              Gérez votre connexion à Sage Business Cloud Accounting
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Statut de connexion
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {sageConnected 
                    ? 'Votre compte Sage est connecté et opérationnel'
                    : 'Connectez votre compte Sage pour utiliser l\'assistant IA'
                  }
                </div>
              </div>
              <Badge variant={sageConnected ? "success" : "secondary"}>
                {sageConnected ? 'Connecté' : 'Déconnecté'}
              </Badge>
            </div>
            
            <Button 
              onClick={handleSageConnection}
              variant={sageConnected ? "outline" : "default"}
            >
              {sageConnected ? (
                <>
                  <Unlink className="h-4 w-4 mr-2" />
                  Déconnecter Sage
                </>
              ) : (
                <>
                  <LinkIcon className="h-4 w-4 mr-2" />
                  Connecter Sage
                </>
              )}
            </Button>

            {!sageConnected && (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Vous devez connecter votre compte Sage Business Cloud pour utiliser 
                  toutes les fonctionnalités de l'assistant IA comptable.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Mot de passe */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>Sécurité</span>
            </CardTitle>
            <CardDescription>
              Modifiez votre mot de passe
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePasswordUpdate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Mot de passe actuel</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData(prev => ({
                    ...prev,
                    currentPassword: e.target.value
                  }))}
                  disabled={loading}
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="newPassword">Nouveau mot de passe</Label>
                  <Input
                    id="newPassword"
                    type="password"
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData(prev => ({
                      ...prev,
                      newPassword: e.target.value
                    }))}
                    disabled={loading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirmer le mot de passe</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData(prev => ({
                      ...prev,
                      confirmPassword: e.target.value
                    }))}
                    disabled={loading}
                  />
                </div>
              </div>
              <Button type="submit" disabled={loading}>
                <Save className="h-4 w-4 mr-2" />
                Mettre à jour le mot de passe
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>Notifications</span>
            </CardTitle>
            <CardDescription>
              Gérez vos préférences de notification
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Notifications par email
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Recevez des notifications importantes par email
                </div>
              </div>
              <Switch
                checked={notifications.emailNotifications}
                onCheckedChange={(checked) => handleNotificationChange('emailNotifications', checked)}
              />
            </div>
            
            <Separator />
            
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Notifications push
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Recevez des notifications directement dans votre navigateur
                </div>
              </div>
              <Switch
                checked={notifications.pushNotifications}
                onCheckedChange={(checked) => handleNotificationChange('pushNotifications', checked)}
              />
            </div>
            
            <Separator />
            
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Rapports hebdomadaires
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Recevez un résumé hebdomadaire de votre activité
                </div>
              </div>
              <Switch
                checked={notifications.weeklyReports}
                onCheckedChange={(checked) => handleNotificationChange('weeklyReports', checked)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Thème */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Palette className="h-5 w-5" />
              <span>Apparence</span>
            </CardTitle>
            <CardDescription>
              Personnalisez l'apparence de l'application
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label className="text-base font-medium">Thème</Label>
                <div className="grid grid-cols-3 gap-3 mt-2">
                  {[
                    { value: 'light', label: 'Clair' },
                    { value: 'dark', label: 'Sombre' },
                    { value: 'system', label: 'Système' }
                  ].map((option) => (
                    <Button
                      key={option.value}
                      variant={theme === option.value ? "default" : "outline"}
                      onClick={() => setTheme(option.value)}
                      className="justify-center"
                    >
                      {option.label}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Zone dangereuse */}
        <Card className="border-red-200 dark:border-red-800">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-red-600 dark:text-red-400">
              <AlertTriangle className="h-5 w-5" />
              <span>Zone dangereuse</span>
            </CardTitle>
            <CardDescription>
              Actions irréversibles sur votre compte
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                  Supprimer le compte
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Une fois supprimé, votre compte et toutes vos données seront définitivement perdues.
                </p>
                <Button 
                  variant="destructive" 
                  onClick={handleDeleteAccount}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Supprimer mon compte
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

