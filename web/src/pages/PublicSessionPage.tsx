import type { Message } from '@/types/chat'
import { Bot, Globe } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useTitle } from '@/hooks/useTitle'
import { apiGet } from '@/lib/api'

interface PublicSession {
  id: string
  title: string
  messages: Array<{
    id: string
    session_id: string
    role: 'user' | 'assistant'
    content: string
    tool_calls: string | null
    created_at: string
  }>
  created_at: string
  updated_at: string
}

function parseMessages(raw: PublicSession['messages']): Message[] {
  return raw.map(m => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: new Date(m.created_at),
  }))
}

export function PublicSessionPage() {
  const { sessionId } = useParams()
  const [session, setSession] = useState<PublicSession | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useTitle(session?.title || 'Shared Session')

  useEffect(() => {
    if (!sessionId)
      return
    apiGet<PublicSession>(`/api/v1/chat/sessions/${sessionId}/public`)
      .then(setSession)
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Session not found or not public')
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <div className="flex gap-1.5">
          <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
          <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
          <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
        </div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-4 text-muted-foreground">
        <Bot className="size-12" />
        <p className="text-lg font-medium">{error || 'Session not found'}</p>
        <a href="/" className="text-sm text-primary hover:underline">Back to Home</a>
      </div>
    )
  }

  const messages = parseMessages(session.messages)

  return (
    <div className="flex h-dvh flex-col bg-background">
      {/* Header */}
      <div className="flex h-14 items-center gap-2 border-b px-6">
        <Globe className="size-4 text-muted-foreground" />
        <h2 className="text-sm font-medium truncate">{session.title}</h2>
        <span className="ml-auto text-xs text-muted-foreground">Public Session</span>
      </div>

      {/* Messages (read-only) */}
      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-3xl space-y-6 p-6">
          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Bot className="mb-3 size-10" />
              <p className="text-sm">This session has no messages yet.</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
