/**
 * 代码块组件：支持语法高亮、特殊语言渲染（HTML/Mermaid/Markdown）、复制按钮。
 */
import type { ComponentPropsWithoutRef } from 'react'
import { Check, ClipboardCopy, Eye, EyeOff, Maximize2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { codeToHtml } from 'shiki'
import { toast } from 'sonner'

// 特殊渲染语言
const RENDERABLE_LANGS = new Set(['html', 'mermaid', 'markdown', 'md'])

/** 从 className 中提取语言名（如 "language-python" → "python"） */
function extractLang(className?: string): string {
  if (!className)
    return ''
  const match = className.match(/language-(\S+)/)
  return match ? match[1] : ''
}

/** Mermaid 图表渲染组件 */
function MermaidRenderer({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    let cancelled = false
    import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({ startOnLoad: false, theme: 'default' })
      const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2)}`
      mermaid.render(id, code).then(({ svg: renderedSvg }) => {
        if (!cancelled)
          setSvg(renderedSvg)
      }).catch((e) => {
        if (!cancelled)
          setError(String(e))
      })
    })
    return () => {
      cancelled = true
    }
  }, [code])

  // ESC 关闭全屏
  useEffect(() => {
    if (!fullscreen)
      return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape')
        setFullscreen(false)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [fullscreen])

  if (error)
    return <div className="text-xs text-destructive p-2">{error}</div>
  if (!svg)
    return <div className="text-xs text-muted-foreground p-2 animate-pulse">Rendering diagram...</div>

  return (
    <>
      <div
        ref={containerRef}
        className="relative flex justify-center overflow-x-auto py-2 cursor-pointer group/mermaid"
        onClick={() => setFullscreen(true)}
        title="Click to fullscreen"
      >
        <button
          type="button"
          className="absolute right-2 top-2 z-10 rounded border bg-background/80 p-1 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover/mermaid:opacity-100"
          onClick={(e) => {
            e.stopPropagation()
            setFullscreen(true)
          }}
        >
          <Maximize2 className="size-3.5" />
        </button>
        {/* eslint-disable-next-line react-dom/no-dangerously-set-innerhtml */}
        <div dangerouslySetInnerHTML={{ __html: svg }} />
      </div>

      {/* 全屏遮罩 */}
      {fullscreen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-6"
          onClick={() => setFullscreen(false)}
        >
          <div
            className="relative max-w-[95vw] max-h-[95vh] overflow-auto rounded-lg bg-background p-6 shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setFullscreen(false)}
              className="absolute right-3 top-3 z-10 rounded-full border bg-background p-1.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="size-4" />
            </button>
            <div
              className="flex justify-center [&_svg]:max-w-full [&_svg]:h-auto"
              // eslint-disable-next-line react-dom/no-dangerously-set-innerhtml
              dangerouslySetInnerHTML={{ __html: svg }}
            />
          </div>
        </div>
      )}
    </>
  )
}

/** HTML 预览组件 */
function HtmlRenderer({ code }: { code: string }) {
  return (
    <iframe
      srcDoc={code}
      className="w-full min-h-[120px] max-h-[400px] border rounded bg-white"
      sandbox="allow-scripts"
      title="HTML Preview"
    />
  )
}

/** Markdown 预览组件 */
function MarkdownRenderer({ code }: { code: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none p-3 border rounded bg-background">
      <Markdown remarkPlugins={[remarkGfm]}>{code}</Markdown>
    </div>
  )
}

export function CodeBlock({ children, className, ...props }: ComponentPropsWithoutRef<'code'>) {
  const [copied, setCopied] = useState(false)
  const [highlighted, setHighlighted] = useState('')
  const [showPreview, setShowPreview] = useState(true)

  const isInline = !className && typeof children === 'string' && !children.includes('\n')

  const lang = extractLang(className)
  const text = useMemo(
    () => typeof children === 'string' ? children.replace(/\n$/, '') : String(children || '').replace(/\n$/, ''),
    [children],
  )

  const isRenderable = RENDERABLE_LANGS.has(lang)

  // 语法高亮
  useEffect(() => {
    if (isInline || !text)
      return
    let cancelled = false
    codeToHtml(text, {
      lang: lang || 'text',
      theme: 'github-dark',
    }).then((html) => {
      if (!cancelled)
        setHighlighted(html)
    }).catch(() => {
      // fallback to plain text
    })
    return () => {
      cancelled = true
    }
  }, [text, lang, isInline])

  if (isInline) {
    return <code className={`${className || ''} px-1 py-0.5 rounded bg-muted text-[0.85em]`} {...props}>{children}</code>
  }

  function handleCopyCode() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Copied!')
    setTimeout(setCopied, 2000, false)
  }

  return (
    <div className="my-2 rounded-lg border border-border overflow-hidden bg-[#0d1117]">
      {/* Tab header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#161b22] border-b border-border text-xs">
        <span className="text-muted-foreground font-mono">
          {lang || 'text'}
        </span>
        <div className="flex items-center gap-1">
          {isRenderable && (
            <button
              type="button"
              onClick={() => setShowPreview(p => !p)}
              className="flex items-center gap-1 rounded px-1.5 py-0.5 text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors"
              title={showPreview ? 'Show code' : 'Show preview'}
            >
              {showPreview ? <EyeOff className="size-3" /> : <Eye className="size-3" />}
            </button>
          )}
          <button
            type="button"
            onClick={handleCopyCode}
            className="flex items-center gap-1 rounded px-1.5 py-0.5 text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors"
          >
            {copied
              ? <Check className="size-3 text-green-400" />
              : <ClipboardCopy className="size-3" />}
          </button>
        </div>
      </div>

      {/* Preview mode for special languages */}
      {isRenderable && showPreview
        ? (
            <div className="bg-background">
              {lang === 'mermaid' && <MermaidRenderer code={text} />}
              {lang === 'html' && <HtmlRenderer code={text} />}
              {(lang === 'markdown' || lang === 'md') && <MarkdownRenderer code={text} />}
            </div>
          )
        : (
            <div className="overflow-x-auto">
              {highlighted
                ? (
                    <div
                      className="[&_pre]:!bg-transparent [&_pre]:p-3 [&_pre]:m-0 [&_code]:text-xs [&_code]:leading-relaxed"
                      // eslint-disable-next-line react-dom/no-dangerously-set-innerhtml
                      dangerouslySetInnerHTML={{ __html: highlighted }}
                    />
                  )
                : (
                    <pre className="p-3 m-0 overflow-x-auto">
                      <code className={`${className || ''} text-xs leading-relaxed text-[#e6edf3]`} {...props}>{children}</code>
                    </pre>
                  )}
            </div>
          )}
    </div>
  )
}
