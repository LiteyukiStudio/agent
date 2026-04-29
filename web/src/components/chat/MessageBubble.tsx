import type { ComponentPropsWithoutRef } from 'react'
import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, ChevronDown, ChevronRight, ExternalLink, User } from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ToolCallCard } from '@/components/chat/ToolCallCard'
import { useAuth } from '@/hooks/useAuth'
import type { Message } from '@/types/chat'

interface MessageBubbleProps {
  message: Message
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

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const { user } = useAuth()

  return (
    <div className={`flex gap-3 min-w-0 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar className="mt-0.5 size-8 shrink-0">
        {isUser && user?.avatar_url && <AvatarImage src={user.avatar_url} alt={user.username} />}
        <AvatarFallback className={isUser ? 'bg-primary text-primary-foreground' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'}>
          {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
        </AvatarFallback>
      </Avatar>

      <div className={`min-w-0 max-w-[75%] space-y-1 ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block rounded-2xl px-4 py-2.5 text-sm leading-relaxed max-w-full overflow-hidden ${
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
          <div className={`${isUser ? 'flex flex-col items-end' : ''}`}>
            {message.toolCalls.map(tc => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}

        <p className="px-1 text-[11px] text-muted-foreground">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}
