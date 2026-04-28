import { useCallback, useEffect, useState } from 'react'
import { apiDelete, apiGet, apiPost, streamSSE } from '@/lib/api'
import type { Message, Session, ToolCall } from '@/types/chat'

interface ApiSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export function useChat() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({})

  // Load sessions on mount
  useEffect(() => {
    apiGet<ApiSession[]>('/api/v1/chat/sessions')
      .then((data) => {
        const mapped: Session[] = data.map(s => ({
          id: s.id,
          title: s.title,
          lastMessage: '',
          updatedAt: new Date(s.updated_at),
          messages: [],
        }))
        setSessions(mapped)
        if (mapped.length > 0 && !activeSessionId)
          setActiveSessionId(mapped[0].id)
      })
      .catch(() => {})
  }, [])

  const activeSession = sessions.find(s => s.id === activeSessionId) ?? null
  const activeMessages = activeSessionId ? (messagesBySession[activeSessionId] || []) : []

  // Build the active session with messages
  const activeSessionWithMessages: Session | null = activeSession
    ? { ...activeSession, messages: activeMessages }
    : null

  const setActiveSession = useCallback((id: string) => {
    setActiveSessionId(id)
  }, [])

  const createSession = useCallback(async () => {
    // 防止重复创建：如果当前会话为空（无消息），不新建
    if (activeSessionId) {
      const msgs = messagesBySession[activeSessionId]
      if (!msgs || msgs.length === 0) {
        return // 当前会话还没有消息，不重复创建
      }
    }

    try {
      const data = await apiPost<ApiSession>('/api/v1/chat/sessions', { title: 'New Chat' })
      const newSession: Session = {
        id: data.id,
        title: data.title,
        lastMessage: '',
        updatedAt: new Date(data.updated_at),
        messages: [],
      }
      setSessions(prev => [newSession, ...prev])
      setActiveSessionId(data.id)
    }
    catch {
      // silently fail
    }
  }, [activeSessionId, messagesBySession])

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiDelete(`/api/v1/chat/sessions/${sessionId}`)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
      }
    }
    catch {
      // silently fail
    }
  }, [activeSessionId])

  const renameSession = useCallback(async (sessionId: string, newTitle: string) => {
    if (!newTitle.trim())
      return
    // 目前后端没有 PATCH 端点，先本地更新标题（后续加后端支持）
    setSessions(prev => prev.map(s =>
      s.id === sessionId ? { ...s, title: newTitle.trim() } : s,
    ))
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!activeSessionId || !content.trim() || isLoading)
      return

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    setMessagesBySession((prev) => {
      const msgs = prev[activeSessionId] || []
      return { ...prev, [activeSessionId]: [...msgs, userMsg] }
    })

    setIsLoading(true)

    // Assistant message that we'll build up from SSE events
    const assistantMsgId = `assistant-${Date.now()}`
    let assistantContent = ''
    const toolCalls: ToolCall[] = []
    let toolCallCounter = 0

    try {
      for await (const event of streamSSE(`/api/v1/chat/sessions/${activeSessionId}/messages`, { content: content.trim() })) {
        const eventType = event.event as string

        if (eventType === 'text') {
          assistantContent += event.content as string
          setMessagesBySession((prev) => {
            const msgs = (prev[activeSessionId] || []).filter(m => m.id !== assistantMsgId)
            return {
              ...prev,
              [activeSessionId]: [...msgs, {
                id: assistantMsgId,
                role: 'assistant',
                content: assistantContent,
                timestamp: new Date(),
                toolCalls: toolCalls.length > 0 ? [...toolCalls] : undefined,
              }],
            }
          })
        }
        else if (eventType === 'tool_call') {
          toolCallCounter++
          toolCalls.push({
            id: `tc-${toolCallCounter}`,
            name: event.name as string,
            args: (event.args as Record<string, unknown>) || {},
            status: 'running',
          })
          setMessagesBySession((prev) => {
            const msgs = (prev[activeSessionId] || []).filter(m => m.id !== assistantMsgId)
            return {
              ...prev,
              [activeSessionId]: [...msgs, {
                id: assistantMsgId,
                role: 'assistant',
                content: assistantContent || 'Calling tools...',
                timestamp: new Date(),
                toolCalls: [...toolCalls],
              }],
            }
          })
        }
        else if (eventType === 'tool_result') {
          const tc = toolCalls.find(t => t.name === event.name)
          if (tc) {
            tc.result = event.result as string
            tc.status = 'completed'
          }
          setMessagesBySession((prev) => {
            const msgs = (prev[activeSessionId] || []).filter(m => m.id !== assistantMsgId)
            return {
              ...prev,
              [activeSessionId]: [...msgs, {
                id: assistantMsgId,
                role: 'assistant',
                content: assistantContent || 'Processing...',
                timestamp: new Date(),
                toolCalls: [...toolCalls],
              }],
            }
          })
        }
        else if (eventType === 'error') {
          assistantContent += `\n\n**Error:** ${event.message}`
        }
      }
    }
    catch (err) {
      assistantContent += `\n\n**Error:** ${err instanceof Error ? err.message : 'Unknown error'}`
    }

    // Final update
    if (assistantContent || toolCalls.length > 0) {
      setMessagesBySession((prev) => {
        const msgs = (prev[activeSessionId] || []).filter(m => m.id !== assistantMsgId)
        return {
          ...prev,
          [activeSessionId]: [...msgs, {
            id: assistantMsgId,
            role: 'assistant',
            content: assistantContent || 'Done.',
            timestamp: new Date(),
            toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
          }],
        }
      })
    }

    // Update session last message
    setSessions(prev => prev.map((s) => {
      if (s.id !== activeSessionId)
        return s
      return { ...s, lastMessage: (assistantContent || content.trim()).slice(0, 50), updatedAt: new Date() }
    }))

    setIsLoading(false)
  }, [activeSessionId, isLoading])

  return {
    sessions,
    activeSession: activeSessionWithMessages,
    isLoading,
    setActiveSession,
    createSession,
    deleteSession,
    renameSession,
    sendMessage,
  }
}
