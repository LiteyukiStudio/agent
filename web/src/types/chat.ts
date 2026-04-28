export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
}

export interface Session {
  id: string
  title: string
  lastMessage: string
  updatedAt: Date
  messages: Message[]
}

export interface ChatState {
  sessions: Session[]
  activeSessionId: string | null
  isLoading: boolean
}
