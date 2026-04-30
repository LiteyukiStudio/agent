import type { Message, MessagePart, Session, ToolCall } from '@/types/chat'
import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { useAuth } from '@/hooks/useAuth'
import { apiDelete, apiGet, apiPatch, apiPost, streamSSE } from '@/lib/api'

interface ApiSession {
  id: string
  title: string
  is_public: boolean
  last_message: string | null
  created_at: string
  updated_at: string
}

interface ApiMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  tool_calls: string | null
  status?: string
  created_at: string
}

function parseApiMessages(data: ApiMessage[]): Message[] {
  return data.map((m) => {
    let toolCalls: ToolCall[] | undefined
    let parts: MessagePart[] | undefined

    if (m.tool_calls) {
      try {
        const parsed = JSON.parse(m.tool_calls) as Array<{ name: string, args?: Record<string, unknown>, result?: string, error?: boolean }>
        toolCalls = parsed.map((tc, i) => ({
          id: `tc-${i}`,
          name: tc.name,
          args: tc.args || {},
          result: tc.result,
          status: tc.error ? 'error' as const : 'completed' as const,
        }))
        // 构建 parts：文本 + 工具调用交错排列
        parts = []
        if (m.content) {
          parts.push({ type: 'text', content: m.content })
        }
        for (const tc of toolCalls) {
          parts.push({ type: 'tool_call', toolCall: tc })
        }
      }
      catch {
        // ignore parse error
      }
    }
    return {
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: new Date(m.created_at),
      toolCalls,
      parts,
      status: m.status,
    } as Message & { status?: string }
  })
}

export function useChat() {
  const { user } = useAuth()
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [loadingSessionIds, setLoadingSessionIds] = useState<Set<string>>(() => new Set())
  const [messagesBySession, setMessagesBySession] = useState<Record<string, Message[]>>({})
  const abortRef = useRef<Record<string, AbortController>>({})

  const isLoading = activeSessionId ? loadingSessionIds.has(activeSessionId) : false

  // 在用户认证完成后才加载 sessions
  useEffect(() => {
    if (!user)
      return
    apiGet<ApiSession[]>('/api/v1/chat/sessions')
      .then((data) => {
        const mapped: Session[] = data.map(s => ({
          id: s.id,
          title: s.title,
          isPublic: s.is_public,
          lastMessage: s.last_message || '',
          updatedAt: new Date(s.updated_at),
          messages: [],
        }))
        setSessions(mapped)
        if (mapped.length > 0 && !activeSessionId) {
          setActiveSessionId(mapped[0].id)
        }
      })
      .catch(() => { /* auth guard handles redirect */ })
  // eslint-disable-next-line react/exhaustive-deps
  }, [user])

  // 加载会话消息（切换会话时）
  const loadMessages = useCallback(async (sessionId: string) => {
    if (messagesBySession[sessionId])
      return // 已加载
    try {
      const data = await apiGet<ApiMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`)
      const messages = parseApiMessages(data)
      setMessagesBySession(prev => ({ ...prev, [sessionId]: messages }))
    }
    catch {
      // message load failure is non-critical
    }
  }, [messagesBySession])

  // 切换 session 时自动加载消息
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId)
    }
  }, [activeSessionId, loadMessages])

  // 轮询：如果最后一条 assistant 消息还在 generating，每 2 秒刷新
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  useEffect(() => {
    // 清理之前的轮询
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    if (!activeSessionId)
      return

    const messages = messagesBySession[activeSessionId]
    if (!messages || messages.length === 0)
      return

    // 检查后端返回的最后一条 assistant 是否在 generating
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
    if (!lastAssistant || (lastAssistant as { status?: string }).status !== 'generating')
      return

    // 启动轮询
    pollingRef.current = setInterval(async () => {
      try {
        const data = await apiGet<ApiMessage[]>(`/api/v1/chat/sessions/${activeSessionId}/messages`)
        const updated = parseApiMessages(data)
        setMessagesBySession(prev => ({ ...prev, [activeSessionId]: updated }))

        // 检查是否已完成
        const lastMsg = [...data].reverse().find(m => m.role === 'assistant')
        if (!lastMsg || lastMsg.status !== 'generating') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }
      }
      catch {
        // 轮询失败不处理
      }
    }, 2000)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [activeSessionId, messagesBySession])

  const activeSession = sessions.find(s => s.id === activeSessionId) ?? null
  const activeMessages = activeSessionId ? (messagesBySession[activeSessionId] || []) : []

  const activeSessionWithMessages: Session | null = activeSession
    ? { ...activeSession, messages: activeMessages }
    : null

  const setActiveSession = useCallback((id: string) => {
    setActiveSessionId(id)
  }, [])

  const createSession = useCallback(async (): Promise<Session | null> => {
    // 防止重复创建：如果当前会话为空（无消息），不新建
    if (activeSessionId) {
      const msgs = messagesBySession[activeSessionId]
      if (!msgs || msgs.length === 0) {
        return null
      }
    }

    try {
      const data = await apiPost<ApiSession>('/api/v1/chat/sessions', { title: 'New Chat' })
      const newSession: Session = {
        id: data.id,
        title: data.title,
        isPublic: data.is_public,
        lastMessage: '',
        updatedAt: new Date(data.updated_at),
        messages: [],
      }
      setSessions(prev => [newSession, ...prev])
      setActiveSessionId(data.id)
      return newSession
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create session')
      return null
    }
  }, [activeSessionId, messagesBySession])

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiDelete(`/api/v1/chat/sessions/${sessionId}`)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      setMessagesBySession((prev) => {
        const next = { ...prev }
        delete next[sessionId]
        return next
      })
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
      }
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete session')
    }
  }, [activeSessionId])

  const renameSession = useCallback(async (sessionId: string, newTitle: string) => {
    if (!newTitle.trim())
      return
    try {
      await apiPatch(`/api/v1/chat/sessions/${sessionId}`, { title: newTitle.trim() })
      setSessions(prev => prev.map(s =>
        s.id === sessionId ? { ...s, title: newTitle.trim() } : s,
      ))
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to rename session')
    }
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!activeSessionId || !content.trim() || loadingSessionIds.has(activeSessionId))
      return

    const sid = activeSessionId

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    setMessagesBySession((prev) => {
      const msgs = prev[sid] || []
      return { ...prev, [sid]: [...msgs, userMsg] }
    })

    setLoadingSessionIds(prev => new Set(prev).add(sid))
    const abortController = new AbortController()
    abortRef.current[sid] = abortController

    const assistantMsgId = `assistant-${Date.now()}`
    let assistantContent = ''
    let thinkingContent = ''
    const toolCalls: ToolCall[] = []
    const parts: MessagePart[] = []
    let toolCallCounter = 0
    let lastTextPartIndex = -1 // 跟踪最后一个 text part 的索引
    let lastThinkingPartIndex = -1 // 跟踪最后一个 thinking part 的索引

    // Helper to build the current assistant message snapshot
    function buildAssistantMsg(contentOverride?: string): Message {
      return {
        id: assistantMsgId,
        role: 'assistant',
        content: contentOverride ?? assistantContent,
        thinking: thinkingContent || undefined,
        timestamp: new Date(),
        toolCalls: toolCalls.length > 0 ? toolCalls.map(tc => ({ ...tc })) : undefined,
        parts: parts.length > 0
          ? parts.map((p) => {
              if (p.type === 'text' || p.type === 'thinking')
                return { ...p }
              return { ...p, toolCall: { ...p.toolCall } }
            })
          : undefined,
      }
    }

    function updateAssistantMsg(contentOverride?: string) {
      setMessagesBySession((prev) => {
        const msgs = (prev[sid] || []).filter(m => m.id !== assistantMsgId)
        return {
          ...prev,
          [sid]: [...msgs, buildAssistantMsg(contentOverride)],
        }
      })
    }

    try {
      for await (const event of streamSSE(`/api/v1/chat/sessions/${sid}/messages`, { content: content.trim() }, abortController.signal)) {
        const eventType = event.event as string

        if (eventType === 'thinking') {
          thinkingContent += event.content as string
          // 追加到 parts：合并连续 thinking 或新建 thinking part
          if (lastThinkingPartIndex >= 0 && parts[lastThinkingPartIndex]?.type === 'thinking'
            && (parts.length - 1 === lastThinkingPartIndex)) {
            ;(parts[lastThinkingPartIndex] as { type: 'thinking', content: string }).content += event.content as string
          }
          else {
            parts.push({ type: 'thinking', content: event.content as string })
            lastThinkingPartIndex = parts.length - 1
          }
          lastTextPartIndex = -1 // thinking 打断连续 text
          updateAssistantMsg()
        }
        else if (eventType === 'text') {
          const text = event.content as string
          assistantContent += text
          // 追加到 parts：合并连续文本或新建 text part
          if (lastTextPartIndex >= 0 && parts[lastTextPartIndex]?.type === 'text'
            && (parts.length - 1 === lastTextPartIndex)) {
            // 最后一个 part 就是 text，直接追加
            ;(parts[lastTextPartIndex] as { type: 'text', content: string }).content += text
          }
          else {
            parts.push({ type: 'text', content: text })
            lastTextPartIndex = parts.length - 1
          }
          lastThinkingPartIndex = -1 // text 打断连续 thinking
          updateAssistantMsg()
        }
        else if (eventType === 'tool_call') {
          toolCallCounter++
          const tc: ToolCall = {
            id: `tc-${toolCallCounter}`,
            name: event.name as string,
            args: (event.args as Record<string, unknown>) || {},
            status: 'running',
          }
          toolCalls.push(tc)
          // 插入到 parts 中对应位置
          const isOptions = tc.name === 'present_options' && tc.args.options
          parts.push({ type: isOptions ? 'options' : 'tool_call', toolCall: tc })
          updateAssistantMsg(assistantContent || 'Calling tools...')
        }
        else if (eventType === 'tool_result') {
          // 找第一个同名且还在 running 的 tool_call
          const tc = toolCalls.find(t => t.name === event.name && t.status === 'running')
          if (tc) {
            tc.result = event.result as string
            tc.status = 'completed'
          }
          updateAssistantMsg(assistantContent || 'Processing...')
        }
        else if (eventType === 'tool_error') {
          // 工具执行出错
          const tc = toolCalls.find(t => t.name === event.name && t.status === 'running')
          if (tc) {
            tc.result = `${event.error_type}: ${event.error_message}`
            tc.status = 'error'
          }
          updateAssistantMsg(assistantContent || 'Processing...')
        }
        else if (eventType === 'error') {
          assistantContent += `\n\n**Error:** ${event.message}`
        }
        else if (eventType === 'done' && event.title) {
          const newTitle = event.title as string
          setSessions(prev => prev.map(s =>
            s.id === sid ? { ...s, title: newTitle } : s,
          ))
        }
      }
    }
    catch (err) {
      // AbortError 是用户主动打断，不显示错误
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 用户主动中断，不追加错误信息
      }
      else {
        assistantContent += `\n\n**Error:** ${err instanceof Error ? err.message : 'Unknown error'}`
      }
    }

    // Final update: mark any still-running tools as error (stream ended unexpectedly)
    for (const tc of toolCalls) {
      if (tc.status === 'running') {
        tc.status = 'error'
        if (!tc.result)
          tc.result = 'Stream ended before tool completed'
      }
    }

    // Final update
    if (assistantContent || thinkingContent || toolCalls.length > 0) {
      updateAssistantMsg(assistantContent || 'Done.')
    }

    // Update session last message
    setSessions(prev => prev.map((s) => {
      if (s.id !== sid)
        return s
      return { ...s, lastMessage: (assistantContent || content.trim()).slice(0, 50), updatedAt: new Date() }
    }))

    setLoadingSessionIds((prev) => {
      const next = new Set(prev)
      next.delete(sid)
      return next
    })
    delete abortRef.current[sid]
  }, [activeSessionId, loadingSessionIds])

  const stopGeneration = useCallback(() => {
    if (activeSessionId && abortRef.current[activeSessionId]) {
      abortRef.current[activeSessionId].abort()
      delete abortRef.current[activeSessionId]
    }
  }, [activeSessionId])

  const togglePublic = useCallback(async (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId)
    if (!session)
      return
    const newPublic = !session.isPublic
    try {
      await apiPatch(`/api/v1/chat/sessions/${sessionId}`, { is_public: newPublic })
      setSessions(prev => prev.map(s =>
        s.id === sessionId ? { ...s, isPublic: newPublic } : s,
      ))
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update session')
    }
  }, [sessions])

  return {
    sessions,
    activeSession: activeSessionWithMessages,
    isLoading,
    setActiveSession,
    createSession,
    deleteSession,
    renameSession,
    sendMessage,
    stopGeneration,
    togglePublic,
  }
}
