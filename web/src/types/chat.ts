export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

export type MessagePart
  = | { type: 'text', content: string }
    | { type: 'thinking', content: string }
    | { type: 'tool_call', toolCall: ToolCall }
    | { type: 'options', toolCall: ToolCall }

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  timestamp: Date
  toolCalls?: ToolCall[]
  /** 交错排列的消息片段（文本 + 工具调用），按时间顺序 */
  parts?: MessagePart[]
}

export interface Session {
  id: string
  title: string
  isPublic: boolean
  lastMessage: string
  updatedAt: Date
  messages: Message[]
}

export interface ChatState {
  sessions: Session[]
  activeSessionId: string | null
  isLoading: boolean
}
