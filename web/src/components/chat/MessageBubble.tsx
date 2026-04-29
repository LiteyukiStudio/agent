import type { ComponentPropsWithoutRef } from 'react'
import { useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUp, Bot, Check, ChevronDown, ChevronRight, ClipboardCopy, ExternalLink, RefreshCw, User } from 'lucide-react'
import { toast } from 'sonner'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ToolCallCard } from '@/components/chat/ToolCallCard'
import { useAuth } from '@/hooks/useAuth'
import type { Message } from '@/types/chat'

interface MessageBubbleProps {
  message: Message
  onRegenerate?: () => void
  onResend?: (content: string) => void
  onSend?: (content: string) => void
}

function ThinkingBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false)

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
        <span>Thinking...</span>
      </button>
      {expanded && (
        <div className="mt-1 border-l-2 border-muted-foreground/20 pl-3 text-xs text-muted-foreground/60 leading-relaxed">
          <div className="prose prose-sm dark:prose-invert max-w-none opacity-60 [&_p]:my-0.5 [&_p]:text-xs [&_code]:text-[11px]">
            <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</Markdown>
          </div>
        </div>
      )}
    </div>
  )
}

const markdownClasses = 'prose prose-sm dark:prose-invert max-w-none break-words overflow-hidden [&_table]:text-xs [&_table]:w-full [&_table]:border-collapse [&_table]:block [&_table]:overflow-x-auto [&_th]:border [&_th]:border-border [&_th]:px-2 [&_th]:py-1 [&_th]:bg-muted [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_pre]:bg-background [&_pre]:text-xs [&_pre]:overflow-x-auto [&_code]:text-xs [&_code]:break-all [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_table]:my-2'

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

const markdownComponents = { a: MarkdownLink }

/** 选项按钮组：支持单选、多选、自由输入 */
function OptionsBlock({ question, options, mode = 'single', icons, onSend }: {
  question?: string
  options: string[]
  mode?: 'single' | 'multiple' | 'free'
  icons?: (string | null)[]
  onSend?: (content: string) => void
}) {
  const [submitted, setSubmitted] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [customValue, setCustomValue] = useState('')
  const [showInput, setShowInput] = useState(mode === 'free')
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSingleSelect(opt: string) {
    if (submitted) return
    setSelected(new Set([opt]))
    setSubmitted(true)
    onSend?.(opt)
  }

  function handleMultiToggle(opt: string) {
    if (submitted) return
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(opt)) next.delete(opt)
      else next.add(opt)
      return next
    })
  }

  function handleMultiSubmit() {
    if (submitted || selected.size === 0) return
    setSubmitted(true)
    onSend?.([...selected].join('、'))
  }

  function handleCustomSubmit() {
    if (!customValue.trim() || submitted) return
    setSubmitted(true)
    setSelected(new Set([customValue.trim()]))
    onSend?.(customValue.trim())
  }

  /** 渲染选项图标：URL → img，emoji/文本 → span，空 → null */
  function renderIcon(index: number) {
    const icon = icons?.[index]
    if (!icon) return null
    if (icon.startsWith('http://') || icon.startsWith('https://')) {
      return <img src={icon} alt="" className="size-4 shrink-0 rounded-sm object-contain" />
    }
    return <span className="text-sm leading-none">{icon}</span>
  }

  return (
    <div className="my-2 space-y-2">
      {question && (
        <p className="text-sm text-muted-foreground">{question}</p>
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
            确认选择 ({selected.size})
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
            onKeyDown={(e) => { if (e.key === 'Enter') handleCustomSubmit() }}
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

export function MessageBubble({ message, onRegenerate, onResend, onSend }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const { user } = useAuth()

  function handleCopy() {
    navigator.clipboard.writeText(message.content)
    toast.success('Copied')
  }

  return (
    <div className={`group/msg flex gap-3 min-w-0 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar className="mt-0.5 size-8 shrink-0">
        {isUser && user?.avatar_url && <AvatarImage src={user.avatar_url} alt={user.username} />}
        <AvatarFallback className={isUser ? 'bg-primary text-primary-foreground' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'}>
          {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
        </AvatarFallback>
      </Avatar>

      <div className={`min-w-0 max-w-[75%] space-y-1 ${isUser ? 'items-end' : ''}`}>
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
                  {message.thinking && (
                    <ThinkingBlock content={message.thinking} />
                  )}
                  <div className={markdownClasses}>
                    <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{message.content}</Markdown>
                  </div>
                </>
              )}
        </div>

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div>
            {message.toolCalls.map((tc) => {
              // present_options: 渲染为可点击的选项按钮
              if (tc.name === 'present_options' && tc.args.options) {
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
              return <ToolCallCard key={tc.id} toolCall={tc} />
            })}
          </div>
        )}

        {/* 时间 + 操作按钮 */}
        <div className={`flex items-center gap-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span className="text-[11px] text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          <div className="flex gap-0.5 opacity-0 transition-opacity group-hover/msg:opacity-100">
            <Button
              variant="ghost"
              size="icon"
              className="size-6 text-muted-foreground hover:text-foreground"
              onClick={handleCopy}
            >
              <ClipboardCopy className="size-3" />
            </Button>
            {isUser && onResend && (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-foreground"
                onClick={() => onResend(message.content)}
              >
                <RefreshCw className="size-3" />
              </Button>
            )}
            {!isUser && onRegenerate && (
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-foreground"
                onClick={onRegenerate}
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
