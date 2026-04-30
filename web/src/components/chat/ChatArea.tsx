import type { Session } from '@/types/chat'
import { Bot, Copy, Eye, EyeOff, MoreHorizontal } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { ChatInput } from '@/components/chat/ChatInput'
import { ConfirmationBanner } from '@/components/chat/ConfirmationBanner'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { ScrollArea } from '@/components/ui/scroll-area'

interface ChatAreaProps {
  session: Session | null
  isLoading: boolean
  onSend: (content: string) => void
  onStop?: () => void
  onTogglePublic?: (sessionId: string) => void
}

export function ChatArea({ session, isLoading, onSend, onStop, onTogglePublic }: ChatAreaProps) {
  const { t } = useTranslation('chat')
  const { t: tc } = useTranslation('common')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session?.messages.length, isLoading])

  if (!session) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-muted-foreground">
        <div className="flex size-16 items-center justify-center rounded-2xl bg-muted">
          <Bot className="size-8" />
        </div>
        <div className="text-center">
          <h2 className="text-lg font-medium text-foreground">{tc('appName')}</h2>
          <p className="mt-1 text-sm">{t('selectSession')}</p>
        </div>
      </div>
    )
  }

  function handleCopyShareLink() {
    if (!session)
      return
    const url = `${window.location.origin}/session/${session.id}/public`
    navigator.clipboard.writeText(url)
    toast.success('Share link copied')
  }

  // 判断是否应该显示加载动画（只在还没有 assistant 内容时）
  const lastMsg = session.messages[session.messages.length - 1]
  const showLoadingDots = isLoading && !(lastMsg?.role === 'assistant' && (lastMsg.content || lastMsg.toolCalls?.length))

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-3 pl-14 sm:px-6 md:pl-6">
        <h2 className="text-sm font-medium truncate">{session.title}</h2>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={(
              <Button variant="ghost" size="icon" className="size-8 shrink-0">
                <MoreHorizontal className="size-4" />
              </Button>
            )}
          />
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => onTogglePublic?.(session.id)}
            >
              {session.isPublic
                ? (
                    <>
                      <EyeOff className="mr-2 size-4" />
                      Set as Private
                    </>
                  )
                : (
                    <>
                      <Eye className="mr-2 size-4" />
                      Set as Public
                    </>
                  )}
            </DropdownMenuItem>
            {session.isPublic && (
              <DropdownMenuItem onClick={handleCopyShareLink}>
                <Copy className="mr-2 size-4" />
                Copy Share Link
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-3xl space-y-6 overflow-hidden px-3 py-4 sm:p-6">
          {session.messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Bot className="mb-3 size-10" />
              <p className="text-sm">{t('noMessages')}</p>
            </div>
          )}
          {session.messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} onSend={onSend} onResend={onSend} />
          ))}
          {showLoadingDots && (
            <div className="flex gap-3">
              <div className="flex size-8 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900">
                <Bot className="size-4 text-emerald-700 dark:text-emerald-300" />
              </div>
              <div className="rounded-2xl rounded-tl-md bg-muted px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                  <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                  <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
          {/* 危险操作确认（内联在消息流中） */}
          <ConfirmationBanner />
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <ChatInput onSend={onSend} onStop={onStop} isLoading={isLoading} />
    </div>
  )
}
