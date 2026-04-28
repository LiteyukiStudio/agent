import { MessageSquarePlus, Settings, Snowflake } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { ThemeToggle } from '@/components/chat/ThemeToggle'
import { cn } from '@/lib/utils'
import type { Session } from '@/types/chat'

interface SidebarProps {
  sessions: Session[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onNewSession: () => void
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

export function Sidebar({ sessions, activeSessionId, onSelectSession, onNewSession }: SidebarProps) {
  return (
    <div className="flex h-full w-[280px] flex-col border-r bg-sidebar">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2.5 px-4">
        <div className="flex size-8 items-center justify-center rounded-lg bg-emerald-100 dark:bg-emerald-900">
          <Snowflake className="size-4 text-emerald-700 dark:text-emerald-300" />
        </div>
        <span className="text-sm font-semibold tracking-tight">LiteYuki SRE</span>
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
          New Chat
        </Button>
      </div>

      {/* Session list */}
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1 pb-3">
          {sessions.map(session => (
            <button
              key={session.id}
              type="button"
              onClick={() => onSelectSession(session.id)}
              className={cn(
                'flex w-full flex-col items-start gap-0.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-sidebar-accent',
                activeSessionId === session.id && 'bg-sidebar-accent',
              )}
            >
              <span className="w-full truncate font-medium text-sidebar-foreground">
                {session.title}
              </span>
              <span className="flex w-full items-center justify-between text-xs text-muted-foreground">
                <span className="truncate max-w-[160px]">{session.lastMessage || 'No messages'}</span>
                <span className="shrink-0 ml-2">{formatRelativeTime(session.updatedAt)}</span>
              </span>
            </button>
          ))}
        </div>
      </ScrollArea>

      <Separator />

      {/* Footer */}
      <div className="flex items-center justify-between p-3">
        <Button variant="ghost" size="icon" className="size-8">
          <Settings className="size-4" />
        </Button>
        <ThemeToggle />
      </div>
    </div>
  )
}
