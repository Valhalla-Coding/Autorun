import { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { auth, getToken } from './api'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ConsolePage from './pages/ConsolePage'
import SettingsPage from './pages/SettingsPage'

const AuthContext = createContext(null)
export function useAuth() { return useContext(AuthContext) }

function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (getToken()) {
      auth.me().then(d => setUser(d.data.user)).catch(() => setUser(null)).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username, password) => {
    const data = await auth.login(username, password)
    setUser(data.data.user)
    return data
  }

  const logout = async () => { await auth.logout(); setUser(null) }

  if (loading) return (
    <div className="flex items-center justify-center h-full bg-gray-950">
      <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}

function RequireAuth({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<DashboardPage />} />
            <Route path="console" element={<ConsolePage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
