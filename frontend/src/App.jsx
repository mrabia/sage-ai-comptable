import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider } from '@/components/theme-provider'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { ChatProvider } from '@/contexts/ChatContext'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import ChatPage from '@/pages/ChatPage'
import SettingsPage from '@/pages/SettingsPage'
import Layout from '@/components/Layout'
import './App.css'

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />
}

function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  return isAuthenticated ? <Navigate to="/chat" /> : children
}

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="sage-ai-theme">
      <AuthProvider>
        <ChatProvider>
          <Router>
            <div className="min-h-screen bg-background">
              <Routes>
                {/* Routes publiques */}
                <Route 
                  path="/login" 
                  element={
                    <PublicRoute>
                      <LoginPage />
                    </PublicRoute>
                  } 
                />
                <Route 
                  path="/register" 
                  element={
                    <PublicRoute>
                      <RegisterPage />
                    </PublicRoute>
                  } 
                />
                
                {/* Routes protégées */}
                <Route 
                  path="/chat" 
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <ChatPage />
                      </Layout>
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/settings" 
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <SettingsPage />
                      </Layout>
                    </ProtectedRoute>
                  } 
                />
                
                {/* Redirection par défaut */}
                <Route path="/" element={<Navigate to="/chat" />} />
              </Routes>
              
              <Toaster />
            </div>
          </Router>
        </ChatProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App

