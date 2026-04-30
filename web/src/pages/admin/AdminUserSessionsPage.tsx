import type { Message, MessagePart, ToolCall } from '@/types/chat'
import { ArrowLeft, Bot, MessageSquare } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useTitle } from '@/hooks/useTitle'
import { apiGet } from '@/lib/api'

interface SessionItem {
  id: string
  title: string
  created_at: string | null
  is_public: boolean
}

interface SessionMessages {
  session: { id: string, title: string, user_id: string }
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    tool_calls: string | null
    created_at: string | null
  }>
}

function parseMessages(raw: SessionMessages['messages']): Message[] {
  return raw.map((m) => {
    // 解析工具调用 JSON
    let toolCalls: ToolCall[] | undefined
    let parts: MessagePart[] | undefined

    if (m.tool_calls) {
      try {
        const rawCalls = JSON.parse(m.tool_calls) as Array<{
          name: string
          args?: Record<string, unknown>
          result?: string
          error?: boolean
        }>
        toolCalls = rawCalls.map((tc, i) => ({
          id: `tc-${i}`,
          name: tc.name,
          args: tc.args || {},
          result: tc.result,
          status: tc.error ? 'error' as const : 'completed' as const,
        }))
        // 构建 parts：文本 + 工具调用交错
        parts = []
        if (m.content) {
          parts.push({ type: 'text', content: m.content })
        }
        for (const tc of toolCalls) {
          parts.push({ type: 'tool_call', toolCall: tc })
        }
      }
      catch {
        // JSON 解析失败，忽略工具调用
      }
    }

    return {
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: new Date(m.created_at || ''),
      toolCalls,
      parts,
    }
  })
}

export function AdminUserSessionsPage() {
  const { userId, sessionId } = useParams()
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [sessionData, setSessionData] = useState<SessionMessages | null>(null)
  const [loading, setLoading] = useState(true)
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('chat')

  useTitle(sessionData ? `Admin: ${sessionData.session.title}` : `Admin: ${t('userSessions')}`)

  // 加载会话列表
  useEffect(() => {
    if (!userId)
      return
    if (sessionId)
      return // 查看单个会话时不加载列表
    apiGet<{ sessions: SessionItem[] }>(`/api/v1/admin/users/${userId}/sessions`)
      .then(data => setSessions(data.sessions))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId, sessionId])

  // 加载单个会话消息
  useEffect(() => {
    if (!userId || !sessionId)
      return
    setLoading(true) // eslint-disable-line react/set-state-in-effect
    apiGet<SessionMessages>(`/api/v1/admin/users/${userId}/sessions/${sessionId}/messages`)
      .then(setSessionData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [userId, sessionId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex gap-1.5">
          <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
          <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
          <span className="size-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
        </div>
      </div>
    )
  }

  // 查看单个会话的消息
  if (sessionId && sessionData) {
    const messages = parseMessages(sessionData.messages)
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => navigate(`/admin/users/${userId}/sessions`)}
          >
            <ArrowLeft className="size-4" />
          </Button>
          <h2 className="text-sm font-medium truncate">{sessionData.session.title}</h2>
          <span className="ml-auto text-[10px] text-muted-foreground">{tc('readOnly')}</span>
        </div>
        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl space-y-6 p-6">
            {messages.map(msg => (
              <MessageBubble key={msg.id} message={msg} readOnly />
            ))}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                <Bot className="mb-3 size-10" />
                <p className="text-sm">{tc('noMessagesInSession')}</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    )
  }

  // 会话列表
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          onClick={() => navigate('/admin/users')}
        >
          <ArrowLeft className="size-4" />
        </Button>
        <h2 className="text-lg font-semibold">
          {t('userSessions')}
        </h2>
        <span className="text-sm text-muted-foreground">
          (
          {sessions.length}
          {' '}
          {t('sessions')}
          )
        </span>
      </div>

      {sessions.length === 0
        ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <MessageSquare className="mb-3 size-10" />
              <p className="text-sm">{t('noSessions')}</p>
            </div>
          )
        : (
            <div className="space-y-1">
              {sessions.map(s => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => navigate(`/admin/users/${userId}/sessions/${s.id}`)}
                  className="flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left hover:bg-accent transition-colors"
                >
                  <MessageSquare className="size-4 shrink-0 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.title || t('untitledSession')}</p>
                    <p className="text-xs text-muted-foreground">
                      {s.created_at ? new Date(s.created_at).toLocaleString() : ''}
                      {s.is_public && ` · ${t('public')}`}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
    </div>
  )
}
