import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { Ellipsis, Globe, LogOut, MessageSquarePlus, Pencil, Settings, Shield, Snowflake, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { ThemeToggle } from '@/components/chat/ThemeToggle'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'
import type { Session } from '@/types/chat'

interface SidebarProps {
  sessions: Session[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onNewSession: () => void
  onDeleteSession?: (id: string) => void
  onRenameSession?: (id: string, title: string) => void
}

function formatRelativeTime(date: Date): string {
  const now = Date.now()
  const diff = now - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1)
    return 'just now'
  if (minutes < 60)
    return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24)
    return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const LANGUAGES = [
  { code: 'zh', label: 'languageZh' },
  { code: 'en', label: 'languageEn' },
  { code: 'ja', label: 'languageJa' },
] as const

export function Sidebar({ sessions, activeSessionId, onSelectSession, onNewSession, onDeleteSession, onRenameSession }: SidebarProps) {
  const { t } = useTranslation('chat')
  const { t: tc } = useTranslation('common')
  const { t: ts } = useTranslation('settings')
  const { i18n } = useTranslation()
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  function changeLanguage(lng: string) {
    i18n.changeLanguage(lng)
  }

  function startRename(session: Session) {
    setRenamingId(session.id)
    setRenameValue(session.title)
  }

  function commitRename() {
    if (renamingId && renameValue.trim() && onRenameSession) {
      onRenameSession(renamingId, renameValue.trim())
    }
    setRenamingId(null)
    setRenameValue('')
  }

  return (
    <div className="flex h-full w-[280px] flex-col border-r bg-sidebar">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2.5 px-4">
        <div className="flex size-8 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-900">
          <Snowflake className="size-4 text-emerald-700 dark:text-emerald-300" />
        </div>
        <span className="text-sm font-semibold tracking-tight">{tc('appName')}</span>
      </div>

      <Separator />

      {/* New chat button */}
      <div className="p-3">
        <Button
          variant="outline"
          className="w-full justify-start gap-2 text-sm"
          onClick={onNewSession}
        >
          <MessageSquarePlus className="size-4" />
          {t('newChat')}
        </Button>
      </div>

      {/* Session list */}
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1 pb-3">
          {sessions.map(session => (
            <div
              key={session.id}
              className={cn(
                'group relative flex w-full flex-col items-start gap-0.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-sidebar-accent cursor-pointer',
                activeSessionId === session.id && 'bg-sidebar-accent',
              )}
              onClick={() => onSelectSession(session.id)}
            >
              {renamingId === session.id
                ? (
                    <Input
                      className="h-6 w-full text-sm font-medium"
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      onBlur={commitRename}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter')
                          commitRename()
                        if (e.key === 'Escape') {
                          setRenamingId(null)
                          setRenameValue('')
                        }
                      }}
                      autoFocus
                      onClick={e => e.stopPropagation()}
                    />
                  )
                : (
                    <span className="w-full truncate font-medium text-sidebar-foreground">
                      {session.title}
                    </span>
                  )}
              <span className="flex w-full items-center justify-between text-xs text-muted-foreground">
                <span className="max-w-[160px] truncate">{session.lastMessage || t('noSessionMessages')}</span>
                {/* 时间 + 悬浮三点菜单 */}
                <span className="ml-2 shrink-0">
                  <span className="group-hover:hidden">{formatRelativeTime(session.updatedAt)}</span>
                  <span className="hidden group-hover:inline-flex">
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={
                          <button
                            type="button"
                            className="inline-flex size-5 items-center justify-center rounded hover:bg-sidebar-border"
                            onClick={e => e.stopPropagation()}
                          >
                            <Ellipsis className="size-3.5" />
                          </button>
                        }
                      />
                      <DropdownMenuContent>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); startRename(session) }}>
                          <Pencil className="mr-2 size-3.5" />
                          {tc('rename')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => { e.stopPropagation(); onDeleteSession?.(session.id) }}
                        >
                          <Trash2 className="mr-2 size-3.5" />
                          {tc('delete')}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </span>
                </span>
              </span>
            </div>
          ))}
        </div>
      </ScrollArea>

      <Separator />

      {/* User & Navigation */}
      <div className="space-y-1 p-3">
        {user && (
          <div className="mb-2 flex items-center gap-2 px-1">
            <Avatar className="size-6">
              <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                {user.username.slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <span className="flex-1 truncate text-sm font-medium">{user.username}</span>
          </div>
        )}

        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="flex-1 justify-start gap-2 text-xs" onClick={() => navigate('/settings')}>
            <Settings className="size-3.5" />
            {ts('settings')}
          </Button>

          {isAdmin && (
            <Button variant="ghost" size="sm" className="flex-1 justify-start gap-2 text-xs" onClick={() => navigate('/admin/users')}>
              <Shield className="size-3.5" />
              {ts('admin')}
            </Button>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          <Button variant="ghost" size="sm" className="gap-2 text-xs text-muted-foreground" onClick={logout}>
            <LogOut className="size-3.5" />
            {ts('logout')}
          </Button>
          <div className="flex items-center gap-1">
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button variant="ghost" size="icon" className="size-8">
                    <Globe className="size-4" />
                  </Button>
                }
              />
              <DropdownMenuContent>
                {LANGUAGES.map(lang => (
                  <DropdownMenuItem key={lang.code} onClick={() => changeLanguage(lang.code)}>
                    {tc(lang.label)}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </div>
  )
}
