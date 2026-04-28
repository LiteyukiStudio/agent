import { useCallback, useState } from 'react'
import type { ChatState, Message, Session, ToolCall } from '@/types/chat'

const MOCK_TOOL_CALLS: ToolCall[] = [
  {
    id: 'tc-1',
    name: 'show_gitea_config',
    args: {},
    result: JSON.stringify({ configured: true, base_url: 'https://git.liteyuki.icu', has_token: true, sources: ['file'] }, null, 2),
    status: 'completed',
  },
  {
    id: 'tc-2',
    name: 'list_repo_issues',
    args: { owner: 'liteyuki', repo: 'liteyuki-bot', state: 'open', limit: 10 },
    result: JSON.stringify([
      { number: 42, title: 'Fix memory leak in plugin loader', state: 'open', labels: ['bug'] },
      { number: 38, title: 'Add i18n support for error messages', state: 'open', labels: ['enhancement'] },
      { number: 35, title: 'Update dependency versions', state: 'open', labels: ['maintenance'] },
    ], null, 2),
    status: 'completed',
  },
]

const MOCK_SESSIONS: Session[] = [
  {
    id: 's-1',
    title: 'Gitea Issue Review',
    lastMessage: 'Found 3 open issues in liteyuki-bot',
    updatedAt: new Date(Date.now() - 1000 * 60 * 5),
    messages: [
      {
        id: 'm-1',
        role: 'user',
        content: 'Please check the open issues in the liteyuki-bot repo on Gitea',
        timestamp: new Date(Date.now() - 1000 * 60 * 10),
      },
      {
        id: 'm-2',
        role: 'assistant',
        content: 'Let me check the Gitea configuration and fetch the open issues for you.',
        timestamp: new Date(Date.now() - 1000 * 60 * 9),
        toolCalls: MOCK_TOOL_CALLS,
      },
      {
        id: 'm-3',
        role: 'assistant',
        content: `I found **3 open issues** in the \`liteyuki/liteyuki-bot\` repository:\n\n| # | Title | Labels |\n|---|-------|--------|\n| #42 | Fix memory leak in plugin loader | \`bug\` |\n| #38 | Add i18n support for error messages | \`enhancement\` |\n| #35 | Update dependency versions | \`maintenance\` |\n\nWould you like me to take any action on these issues? For example, I can:\n- Add comments\n- Assign someone\n- Close resolved ones`,
        timestamp: new Date(Date.now() - 1000 * 60 * 8),
      },
    ],
  },
  {
    id: 's-2',
    title: 'Deploy Status Check',
    lastMessage: 'All services are running normally',
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    messages: [
      {
        id: 'm-4',
        role: 'user',
        content: 'What is the current status of all our services?',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
      },
      {
        id: 'm-5',
        role: 'assistant',
        content: 'All services are running normally. The Gitea instance at `git.liteyuki.icu` is online and responsive.',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2 + 5000),
      },
    ],
  },
  {
    id: 's-3',
    title: 'New Repo Setup',
    lastMessage: 'Repository created successfully',
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    messages: [],
  },
]

let messageCounter = 100

function generateId(): string {
  messageCounter += 1
  return `m-${messageCounter}`
}

export function useChat() {
  const [state, setState] = useState<ChatState>({
    sessions: MOCK_SESSIONS,
    activeSessionId: 's-1',
    isLoading: false,
  })

  const activeSession = state.sessions.find(s => s.id === state.activeSessionId) ?? null

  const setActiveSession = useCallback((id: string) => {
    setState(prev => ({ ...prev, activeSessionId: id }))
  }, [])

  const createSession = useCallback(() => {
    const newSession: Session = {
      id: `s-${Date.now()}`,
      title: 'New Chat',
      lastMessage: '',
      updatedAt: new Date(),
      messages: [],
    }
    setState(prev => ({
      ...prev,
      sessions: [newSession, ...prev.sessions],
      activeSessionId: newSession.id,
    }))
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!state.activeSessionId || !content.trim())
      return

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    setState((prev) => {
      const sessions = prev.sessions.map((s) => {
        if (s.id !== prev.activeSessionId)
          return s
        return {
          ...s,
          messages: [...s.messages, userMessage],
          lastMessage: content.trim(),
          updatedAt: new Date(),
        }
      })
      return { ...prev, sessions, isLoading: true }
    })

    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: `I received your message: "${content.trim()}"\n\nThis is a mock response. In production, this would be connected to the ADK Runner API to get real agent responses.`,
        timestamp: new Date(),
      }

      setState((prev) => {
        const sessions = prev.sessions.map((s) => {
          if (s.id !== prev.activeSessionId)
            return s
          return {
            ...s,
            messages: [...s.messages, assistantMessage],
            lastMessage: assistantMessage.content.slice(0, 50),
            updatedAt: new Date(),
          }
        })
        return { ...prev, sessions, isLoading: false }
      })
    }, 1200)
  }, [state.activeSessionId])

  return {
    sessions: state.sessions,
    activeSession,
    isLoading: state.isLoading,
    setActiveSession,
    createSession,
    sendMessage,
  }
}
