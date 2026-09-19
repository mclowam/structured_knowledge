import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { login as loginApi, logout as logoutApi, me, register as registerApi } from '../api/auth'
import { ApiError, getAccessToken } from '../api/client'
import type { UserPayload } from '../types/auth'

interface AuthContextValue {
  user: UserPayload | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPayload | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false)
      return
    }
    me()
      .then(setUser)
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          logoutApi()
        }
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (username: string, password: string) => {
        await loginApi({ username, password })
        setUser(await me())
      },
      register: async (username: string, password: string) => {
        await registerApi({ username, password })
        await loginApi({ username, password })
        setUser(await me())
      },
      logout: () => {
        logoutApi()
        setUser(null)
      },
    }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
