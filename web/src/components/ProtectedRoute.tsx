import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useAuth } from '@/hooks/useAuth'

interface ProtectedRouteProps {
  children: ReactNode
  requireAdmin?: boolean
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
      </div>
    )
  }

  if (!user)
    return <Navigate to="/login" replace />

  if (requireAdmin && user.role !== 'admin' && user.role !== 'superuser') {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-2">
        <h1 className="text-2xl font-bold">403</h1>
        <p className="text-muted-foreground">You do not have permission to access this page</p>
      </div>
    )
  }

  return children
}
