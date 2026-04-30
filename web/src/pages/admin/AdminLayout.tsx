import type { ReactNode } from 'react'
import { ArrowLeft, KeyRound, Shield, Users, Zap } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/oauth', label: 'OAuth', icon: KeyRound },
  { to: '/admin/quota', label: 'Quota Plans', icon: Zap },
]

function NavItem({ to, label, icon: Icon }: { to: string, label: string, icon: React.ComponentType<{ className?: string }> }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => cn(
        'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent',
        isActive && 'bg-accent font-medium',
      )}
    >
      <Icon className="size-4" />
      {label}
    </NavLink>
  )
}

export function AdminLayout({ children }: { children?: ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <aside className="flex w-56 flex-col border-r bg-sidebar p-4">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <Shield className="size-4" />
          Admin
        </div>
        <nav className="flex-1 space-y-1">
          {navItems.map(item => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>
        <NavLink to="/" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-accent">
          <ArrowLeft className="size-4" />
          Back to Chat
        </NavLink>
      </aside>
      <main className="flex-1 overflow-auto">
        {children || <Outlet />}
      </main>
    </div>
  )
}
