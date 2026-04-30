/* eslint-disable react-refresh/only-export-components */
import type { ReactNode } from 'react'
import { createContext, use, useCallback, useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '@/lib/api'

interface User {
  id: string
  username: string
  email: string | null
  avatar_url: string | null
  role: 'superuser' | 'admin' | 'user'
}

interface AuthContextValue {
  user: User | null
  token: string | null
  loading: boolean
  isAdmin: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => {
    // OAuth 回调会在 URL 中带上 oauth_token 参数
    const params = new URLSearchParams(window.location.search)
    const oauthToken = params.get('oauth_token')
    if (oauthToken) {
      localStorage.setItem('token', oauthToken)
      // 清理 URL 中的 token 参数（安全 + 美观）
      params.delete('oauth_token')
      const clean = params.toString()
      const newUrl = window.location.pathname + (clean ? `?${clean}` : '')
      window.history.replaceState({}, '', newUrl)
      return oauthToken
    }
    return localStorage.getItem('token')
  })
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    const stored = localStorage.getItem('token')
    if (!stored) {
      setLoading(false)
      return
    }
    try {
      const u = await apiGet<User>('/api/v1/auth/me')
      setUser(u)
      setToken(stored)
    }
    catch {
      localStorage.removeItem('token')
      setToken(null)
      setUser(null)
    }
    finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiPost<{ access_token: string }>('/api/v1/auth/login', { username, password })
    localStorage.setItem('token', res.access_token)
    setToken(res.access_token)
    const u = await apiGet<User>('/api/v1/auth/me')
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }, [])

  const isAdmin = user?.role === 'admin' || user?.role === 'superuser'

  const value = useMemo(() => ({ user, token, loading, isAdmin, login, logout }), [user, token, loading, isAdmin, login, logout])

  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth(): AuthContextValue {
  const ctx = use(AuthContext)
  if (!ctx)
    throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
