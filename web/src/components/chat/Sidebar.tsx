import type { Session } from '@/types/chat'
import {
  CheckSquare,
  ChevronUp,
  Ellipsis,
  Globe,
  Loader2,
  LogOut,
  MessageSquarePlus,
  Monitor,
  Moon,
  Pencil,
  Settings,
  Shield,
  Snowflake,
  Sun,
  Trash2,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

interface SidebarProps {
  sessions: Session[]
  activeSessionId: string | null
  isLoading?: boolean
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
    return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24)
    return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

const LANGUAGES = [
  { code: 'zh', label: 'languageZh' },
  { code: 'en', label: 'languageEn' },
  { code: 'ja', label: 'languageJa' },
] as const

export function Sidebar({ sessions, activeSessionId, isLoading, onSelectSession, onNewSession, onDeleteSession, onRenameSession }: SidebarProps) {
  const { t } = useTranslation('chat')
  const { t: tc } = useTranslation('common')
  const { t: ts } = useTranslation('settings')
  const { i18n } = useTranslation()
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [batchMode, setBatchMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark' | 'system') || 'system'
  })

  function applyTheme(mode: 'light' | 'dark' | 'system') {
    setTheme(mode)
    localStorage.setItem('theme', mode)
    if (mode === 'system') {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      document.documentElement.classList.toggle('dark', isDark)
    }
    else {
      document.documentElement.classList.toggle('dark', mode === 'dark')
    }
  }

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

  function handleDeleteConfirm() {
    if (deleteConfirmId && onDeleteSession) {
      onDeleteSession(deleteConfirmId)
    }
    setDeleteConfirmId(null)
  }

  return (
    <div className="flex h-full w-[280px] flex-col bg-sidebar">
      {/* 顶部品牌 */}
      <div className="flex h-14 items-center gap-2.5 px-4">
        <div className="flex size-8 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-900">
          <Snowflake className="size-4 text-emerald-700 dark:text-emerald-300" />
        </div>
        <span className="text-sm font-semibold tracking-tight">{tc('appName')}</span>
      </div>

      <Separator />

      {/* 新建对话 + 批量操作 */}
      <div className="p-3">
        {!batchMode
          ? (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1 justify-start gap-2 text-sm"
                  onClick={onNewSession}
                >
                  <MessageSquarePlus className="size-4" />
                  {t('newChat')}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-9 shrink-0 text-muted-foreground"
                  onClick={() => {
                    setBatchMode(true)
                    setSelectedIds(new Set())
                  }}
                  title="批量操作"
                >
                  <CheckSquare className="size-4" />
                </Button>
              </div>
            )
          : (
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  size="sm"
                  className="flex-1 gap-1.5 text-sm"
                  disabled={selectedIds.size === 0}
                  onClick={() => {
                    selectedIds.forEach(id => onDeleteSession?.(id))
                    setBatchMode(false)
                    setSelectedIds(new Set())
                  }}
                >
                  <Trash2 className="size-3.5" />
                  删除 (
                  {selectedIds.size}
                  )
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 text-sm text-muted-foreground"
                  onClick={() => {
                    setBatchMode(false)
                    setSelectedIds(new Set())
                  }}
                >
                  <X className="size-3.5" />
                  取消
                </Button>
              </div>
            )}
      </div>

      {/* 会话列表 */}
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1 pb-3">
          {sessions.map(session => (
            <div
              key={session.id}
              className={cn(
                'group relative flex w-full flex-col items-start gap-0.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-sidebar-accent cursor-pointer',
                batchMode && 'pl-8',
                activeSessionId === session.id && !batchMode && 'bg-sidebar-accent',
                batchMode && selectedIds.has(session.id) && 'bg-destructive/10 border border-destructive/30',
              )}
              onClick={() => {
                if (batchMode) {
                  setSelectedIds((prev) => {
                    const next = new Set(prev)
                    if (next.has(session.id))
                      next.delete(session.id)
                    else next.add(session.id)
                    return next
                  })
                }
                else {
                  onSelectSession(session.id)
                }
              }}
            >
              {/* 批量选择模式下的复选框 */}
              {batchMode && (
                <div className="absolute left-2 top-1/2 -translate-y-1/2">
                  <div className={cn(
                    'size-4 rounded border-2 flex items-center justify-center transition-colors',
                    selectedIds.has(session.id)
                      ? 'bg-destructive border-destructive text-destructive-foreground'
                      : 'border-muted-foreground/40',
                  )}
                  >
                    {selectedIds.has(session.id) && <CheckSquare className="size-3" />}
                  </div>
                </div>
              )}
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
                    <span className="flex w-full items-center gap-1.5 font-medium text-sidebar-foreground">
                      <span className="truncate">{session.title}</span>
                      {isLoading && activeSessionId === session.id && (
                        <Loader2 className="size-3.5 shrink-0 animate-spin text-muted-foreground" />
                      )}
                    </span>
                  )}
              <span className="flex w-full items-center justify-between text-xs text-muted-foreground">
                <span className="max-w-[140px] truncate">{session.lastMessage || t('noSessionMessages')}</span>
                {/* 桌面端 hover 显示，移动端始终显示 */}
                <span className="relative ml-2 shrink-0">
                  <span className="transition-opacity group-hover:opacity-0 max-sm:hidden">{formatRelativeTime(session.updatedAt)}</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={(
                        <button
                          type="button"
                          className="absolute inset-0 flex items-center justify-center rounded transition-opacity hover:bg-muted opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
                          onClick={e => e.stopPropagation()}
                        >
                          <Ellipsis className="size-3.5" />
                        </button>
                      )}
                    />
                    <DropdownMenuContent align="end" side="bottom">
                      <DropdownMenuItem onClick={() => startRename(session)}>
                        <Pencil className="mr-2 size-3.5" />
                        {tc('rename')}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        variant="destructive"
                        onClick={() => setDeleteConfirmId(session.id)}
                      >
                        <Trash2 className="mr-2 size-3.5" />
                        {tc('delete')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </span>
              </span>
            </div>
          ))}
        </div>
      </ScrollArea>

      <Separator />

      {/* 底部用户菜单 */}
      <div className="p-3">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={(
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-sidebar-accent"
              >
                <Avatar className="size-7">
                  {user?.avatar_url && <AvatarImage src={user.avatar_url} alt={user.username} />}
                  <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                    {user?.username.slice(0, 2).toUpperCase() || '?'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 overflow-hidden">
                  <p className="truncate text-sm font-medium">{user?.username}</p>
                  <p className="truncate text-xs text-muted-foreground">{user?.email || user?.role}</p>
                </div>
                <ChevronUp className="size-4 text-muted-foreground" />
              </button>
            )}
          />
          <DropdownMenuContent side="top" align="start" className="w-[248px]">
            <DropdownMenuItem onClick={() => navigate('/settings')}>
              <Settings className="mr-2 size-4" />
              {ts('settings')}
            </DropdownMenuItem>

            {isAdmin && (
              <DropdownMenuItem onClick={() => navigate('/admin/users')}>
                <Shield className="mr-2 size-4" />
                {ts('admin')}
              </DropdownMenuItem>
            )}

            <DropdownMenuSeparator />

            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                {theme === 'dark'
                  ? <Moon className="mr-2 size-4" />
                  : theme === 'light'
                    ? <Sun className="mr-2 size-4" />
                    : <Monitor className="mr-2 size-4" />}
                {tc('theme')}
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem onClick={() => applyTheme('light')}>
                  <Sun className="mr-2 size-4" />
                  {tc('lightMode')}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => applyTheme('dark')}>
                  <Moon className="mr-2 size-4" />
                  {tc('darkMode')}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => applyTheme('system')}>
                  <Monitor className="mr-2 size-4" />
                  {tc('autoMode')}
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>

            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <Globe className="mr-2 size-4" />
                {tc('language')}
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                {LANGUAGES.map(lang => (
                  <DropdownMenuItem key={lang.code} onClick={() => changeLanguage(lang.code)}>
                    {tc(lang.label)}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuSubContent>
            </DropdownMenuSub>

            <DropdownMenuSeparator />

            <DropdownMenuItem variant="destructive" onClick={logout}>
              <LogOut className="mr-2 size-4" />
              {ts('logout')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* 删除确认对话框 */}
      <ConfirmDialog
        open={!!deleteConfirmId}
        onOpenChange={open => !open && setDeleteConfirmId(null)}
        title={tc('confirmDelete')}
        description={tc('confirmDeleteSession')}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  )
}
