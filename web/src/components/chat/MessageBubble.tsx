import type { ComponentPropsWithoutRef } from 'react'
import type { Message, MessagePart, ToolCall } from '@/types/chat'
import { ArrowUp, Bot, Check, ChevronDown, ChevronRight, ClipboardCopy, ExternalLink, RefreshCw, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'
import { ToolCallCard } from '@/components/chat/ToolCallCard'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/useAuth'

interface MessageBubbleProps {
  message: Message
  onRegenerate?: () => void
  onResend?: (content: string) => void
  onSend?: (content: string) => void
  /** 只读模式：不使用当前登录用户头像（用于 admin 查看他人会话） */
  readOnly?: boolean
}

const markdownClasses = 'prose prose-sm dark:prose-invert max-w-none break-words overflow-hidden [&_table]:text-xs [&_table]:w-full [&_table]:border-collapse [&_table]:block [&_table]:overflow-x-auto [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_pre]:bg-background [&_pre]:text-xs [&_pre]:overflow-x-auto [&_pre]:max-w-full [&_code]:text-xs [&_code]:break-all [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_table]:my-2'

// External links: primary color + icon + new tab; internal links: default
function MarkdownLink({ href, children, ...props }: ComponentPropsWithoutRef<'a'>) {
  const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'))
    && !href.startsWith(window.location.origin)
  if (isExternal) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-0.5 text-primary no-underline hover:underline"
        {...props}
      >
        {children}
        <ExternalLink className="inline size-3 shrink-0" />
      </a>
    )
  }
  return <a href={href} {...props}>{children}</a>
}

/** 代码块：右上角带复制按钮 */
function CodeBlock({ children, className, ...props }: ComponentPropsWithoutRef<'code'>) {
  const [copied, setCopied] = useState(false)
  const isInline = !className && typeof children === 'string' && !children.includes('\n')

  if (isInline) {
    return <code className={className} {...props}>{children}</code>
  }

  const text = typeof children === 'string' ? children : String(children || '').replace(/\n$/, '')

  function handleCopyCode() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(setCopied, 2000, false)
  }

  return (
    <div className="relative group/code">
      <button
        type="button"
        onClick={handleCopyCode}
        className="absolute right-2 top-2 z-10 rounded border bg-background/80 p-1 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover/code:opacity-100 active:opacity-100"
      >
        {copied ? <Check className="size-3" /> : <ClipboardCopy className="size-3" />}
      </button>
      <code className={className} {...props}>{children}</code>
    </div>
  )
}

const markdownComponents = { a: MarkdownLink, code: CodeBlock }

function ThinkingBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false)
  const previewRef = useRef<HTMLDivElement>(null)
  const lines = content.split('\n').filter(Boolean)
  const previewLines = lines.slice(-3)

  // 自动滚动到最新内容
  useEffect(() => {
    if (previewRef.current && !expanded) {
      previewRef.current.scrollTop = previewRef.current.scrollHeight
    }
  }, [content, expanded])

  return (
    <div className="mb-1.5">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1 text-xs text-muted-foreground/70 hover:text-muted-foreground transition-colors"
      >
        {expanded
          ? <ChevronDown className="size-3" />
          : <ChevronRight className="size-3" />}
        <span className="animate-pulse">Thinking...</span>
      </button>
      {expanded
        ? (
            <div className="mt-1 border-l-2 border-muted-foreground/20 pl-3 text-xs text-muted-foreground/60 leading-relaxed max-h-60 overflow-y-auto">
              <div className="prose prose-sm dark:prose-invert max-w-none opacity-60 [&_p]:my-0.5 [&_p]:text-xs [&_code]:text-[11px]">
                <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</Markdown>
              </div>
            </div>
          )
        : (
            <div
              ref={previewRef}
              className="mt-1 border-l-2 border-muted-foreground/20 pl-3 text-xs text-muted-foreground/50 leading-relaxed max-h-[3.6em] overflow-hidden"
            >
              {previewLines.map((line, i) => (
                // eslint-disable-next-line react/no-array-index-key
                <div key={i} className="truncate">{line}</div>
              ))}
            </div>
          )}
    </div>
  )
}

/** 选项按钮组：支持单选、多选、自由输入 */
function OptionsBlock({ question, options, mode = 'single', icons, onSend }: {
  question?: string
  options: string[]
  mode?: 'single' | 'multiple' | 'free'
  icons?: (string | null)[]
  onSend?: (content: string) => void
}) {
  const [submitted, setSubmitted] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [customValue, setCustomValue] = useState('')
  const [showInput, setShowInput] = useState(mode === 'free')
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSingleSelect(opt: string) {
    if (submitted)
      return
    setSelected(new Set([opt]))
    setSubmitted(true)
    onSend?.(opt)
  }

  function handleMultiToggle(opt: string) {
    if (submitted)
      return
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(opt))
        next.delete(opt)
      else next.add(opt)
      return next
    })
  }

  function handleMultiSubmit() {
    if (submitted || selected.size === 0)
      return
    setSubmitted(true)
    onSend?.([...selected].join('、'))
  }

  function handleCustomSubmit() {
    if (!customValue.trim() || submitted)
      return
    setSubmitted(true)
    setSelected(new Set([customValue.trim()]))
    onSend?.(customValue.trim())
  }

  /** 渲染选项图标：URL → img，emoji/文本 → span，空 → null */
  function renderIcon(index: number) {
    const icon = icons?.[index]
    if (!icon)
      return null
    if (icon.startsWith('http://') || icon.startsWith('https://')) {
      return <img src={icon} alt="" className="size-4 shrink-0 rounded-sm object-contain" />
    }
    return <span className="text-sm leading-none">{icon}</span>
  }

  return (
    <div className="my-2 space-y-2 max-w-full overflow-hidden">
      {question && (
        <p className="text-sm text-muted-foreground break-words">{question}</p>
      )}

      {/* 选项按钮 */}
      <div className="flex flex-wrap gap-2">
        {options.map((opt, idx) => {
          const isSelected = selected.has(opt)
          const icon = renderIcon(idx)
          if (mode === 'single') {
            return (
              <Button
                key={opt}
                variant={isSelected ? 'default' : 'outline'}
                size="sm"
                className="rounded-full gap-1.5"
                disabled={submitted && !isSelected}
                onClick={() => handleSingleSelect(opt)}
              >
                {icon}
                {opt}
              </Button>
            )
          }
          // multiple / free: checkbox 风格
          return (
            <Button
              key={opt}
              variant={isSelected ? 'default' : 'outline'}
              size="sm"
              className="rounded-full gap-1.5"
              disabled={submitted}
              onClick={() => handleMultiToggle(opt)}
            >
              {isSelected && <Check className="size-3" />}
              {!isSelected && icon}
              {opt}
            </Button>
          )
        })}

        {/* 单选模式下的自定义按钮 */}
        {mode === 'single' && !submitted && !showInput && (
          <Button
            variant="ghost"
            size="sm"
            className="rounded-full text-muted-foreground"
            onClick={() => {
              setShowInput(true)
              setTimeout(() => inputRef.current?.focus(), 0)
            }}
          >
            自定义...
          </Button>
        )}

        {/* 多选模式下的确认按钮 */}
        {mode === 'multiple' && !submitted && selected.size > 0 && (
          <Button
            size="sm"
            className="rounded-full"
            onClick={handleMultiSubmit}
          >
            确认选择 (
            {selected.size}
            )
          </Button>
        )}
      </div>

      {/* 自定义输入框（单选的"自定义..." / free 模式始终显示） */}
      {showInput && !submitted && (
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={customValue}
            onChange={e => setCustomValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter')
                handleCustomSubmit()
            }}
            placeholder={mode === 'free' ? '输入你的回答（也可点击上方建议）' : '输入你的回答'}
            className="h-8 text-sm"
          />
          <Button
            size="icon"
            className="size-8 shrink-0"
            disabled={!customValue.trim()}
            onClick={handleCustomSubmit}
          >
            <ArrowUp className="size-3.5" />
          </Button>
        </div>
      )}
    </div>
  )
}

const TOOL_CALLS_COLLAPSE_THRESHOLD = 3

/** 连续工具调用组：超过阈值时折叠 */
function ToolCallGroup({ toolCalls }: { toolCalls: ToolCall[] }) {
  const [expanded, setExpanded] = useState(false)
  const { t } = useTranslation('chat')

  if (toolCalls.length <= TOOL_CALLS_COLLAPSE_THRESHOLD) {
    return (
      <>
        {toolCalls.map(tc => <ToolCallCard key={tc.id} toolCall={tc} />)}
      </>
    )
  }

  const visibleCalls = expanded ? toolCalls : toolCalls.slice(-TOOL_CALLS_COLLAPSE_THRESHOLD)
  const hiddenCount = toolCalls.length - (expanded ? toolCalls.length : TOOL_CALLS_COLLAPSE_THRESHOLD)
  const completedCount = toolCalls.filter(tc => tc.status === 'completed').length
  const runningCount = toolCalls.filter(tc => tc.status === 'running').length
  const errorCount = toolCalls.filter(tc => tc.status === 'error').length

  return (
    <div className="space-y-1">
      {!expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="flex items-center gap-1.5 rounded-lg border border-dashed px-2.5 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <ChevronRight className="size-3" />
          <span>{t('toolCollapse', { count: toolCalls.length })}</span>
          {runningCount > 0 && (
            <span className="text-[10px] text-blue-600">
              ·
              {runningCount}
              {' '}
              {t('toolStatus.running')}
            </span>
          )}
          {completedCount > 0 && (
            <span className="text-[10px] text-emerald-600">
              ·
              {completedCount}
              {' '}
              {t('toolStatus.completed')}
            </span>
          )}
          {errorCount > 0 && (
            <span className="text-[10px] text-red-600">
              ·
              {errorCount}
              {' '}
              {t('toolStatus.error')}
            </span>
          )}
        </button>
      )}
      {expanded && hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="flex items-center gap-1.5 rounded-lg border border-dashed px-2.5 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <ChevronDown className="size-3" />
          <span>{t('toolCollapseHide')}</span>
        </button>
      )}
      {visibleCalls.map(tc => <ToolCallCard key={tc.id} toolCall={tc} />)}
    </div>
  )
}

/** 渲染交错排列的消息内容（文本 + thinking + 工具调用） */
function InterleavedParts({ parts, onSend }: { parts: MessagePart[], onSend?: (content: string) => void }) {
  // 将连续的 tool_call 分组
  const groups: Array<
    | { type: 'text', content: string }
    | { type: 'thinking', content: string }
    | { type: 'tool_calls', calls: ToolCall[] }
    | { type: 'options', toolCall: ToolCall }
  > = []

  for (const part of parts) {
    if (part.type === 'text') {
      groups.push({ type: 'text', content: part.content })
    }
    else if (part.type === 'thinking') {
      groups.push({ type: 'thinking', content: part.content })
    }
    else if (part.type === 'options') {
      groups.push({ type: 'options', toolCall: part.toolCall })
    }
    else {
      // tool_call: 和前一个 tool_calls 组合并
      const last = groups[groups.length - 1]
      if (last && last.type === 'tool_calls') {
        last.calls.push(part.toolCall)
      }
      else {
        groups.push({ type: 'tool_calls', calls: [part.toolCall] })
      }
    }
  }

  return (
    <>
      {groups.map((group, i) => {
        if (group.type === 'thinking') {
          // eslint-disable-next-line react/no-array-index-key
          return <ThinkingBlock key={`think-${i}`} content={group.content} />
        }
        if (group.type === 'text') {
          return (
            // eslint-disable-next-line react/no-array-index-key
            <div key={`text-${i}`} className={markdownClasses}>
              <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{group.content}</Markdown>
            </div>
          )
        }
        if (group.type === 'options') {
          const tc = group.toolCall
          const options = tc.args.options as string[]
          const question = tc.args.question as string | undefined
          const mode = (tc.args.mode as 'single' | 'multiple' | 'free') || 'single'
          const icons = (tc.args.icons as (string | null)[] | undefined) || undefined
          return (
            <OptionsBlock
              key={tc.id}
              question={question}
              options={options}
              mode={mode}
              icons={icons}
              onSend={onSend}
            />
          )
        }
        // tool_calls group
        // eslint-disable-next-line react/no-array-index-key
        return <ToolCallGroup key={`tc-group-${i}`} toolCalls={group.calls} />
      })}
    </>
  )
}

export function MessageBubble({ message, onRegenerate, onResend, onSend, readOnly }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const { user } = useAuth()
  const [showActions, setShowActions] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(message.content)
    toast.success('Copied')
  }

  function handleTap() {
    // 移动端点击消息切换按钮显示
    setShowActions(prev => !prev)
  }

  return (
    <div className={`group/msg flex gap-3 min-w-0 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar className="mt-0.5 size-8 shrink-0">
        {isUser && !readOnly && user?.avatar_url && <AvatarImage src={user.avatar_url} alt={user.username} />}
        <AvatarFallback className={isUser ? 'bg-primary text-primary-foreground' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'}>
          {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
        </AvatarFallback>
      </Avatar>

      <div
        className={`min-w-0 max-w-[85%] sm:max-w-[75%] space-y-1 overflow-hidden ${isUser ? 'items-end' : ''}`}
        onClick={handleTap}
      >
        <div
          className={`inline-block rounded-2xl px-4 py-2.5 text-sm leading-relaxed max-w-full overflow-hidden text-left ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-md'
              : 'bg-muted rounded-tl-md'
          }`}
        >
          {isUser
            ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )
            : (
                <>
                  {message.thinking && (!message.parts || message.parts.length === 0) && (
                    <ThinkingBlock content={message.thinking} />
                  )}
                  {message.parts && message.parts.length > 0
                    ? <InterleavedParts parts={message.parts} onSend={onSend} />
                    : (
                        <div className={markdownClasses}>
                          <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{message.content}</Markdown>
                        </div>
                      )}
                </>
              )}
        </div>

        {/* 时间 + 操作按钮（紧贴消息底部） */}
        <div className={`flex items-center gap-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span className="text-[11px] text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          <div className={`flex gap-0.5 transition-opacity ${showActions ? 'opacity-100' : 'opacity-0 group-hover/msg:opacity-100'}`}>
            <Button
              variant="ghost"
              size="icon"
              className="size-6 text-muted-foreground hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation()
                handleCopy()
              }}
            >
              <ClipboardCopy className="size-3" />
            </Button>
            {isUser && onResend && (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-foreground"
                onClick={(e) => {
                  e.stopPropagation()
                  onResend(message.content)
                }}
              >
                <RefreshCw className="size-3" />
              </Button>
            )}
            {!isUser && onRegenerate && (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-foreground"
                onClick={(e) => {
                  e.stopPropagation()
                  onRegenerate()
                }}
              >
                <RefreshCw className="size-3" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
