import type { KeyboardEvent } from 'react'
import { useCallback, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowUp, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

interface ChatInputProps {
  onSend: (content: string) => void
  onStop?: () => void
  isLoading: boolean
  disabled?: boolean
}

export function ChatInput({ onSend, onStop, isLoading, disabled }: ChatInputProps) {
  const { t } = useTranslation('chat')
  const { t: tc } = useTranslation('common')
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = useCallback(() => {
    if (!value.trim() || isLoading || disabled)
      return
    onSend(value)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value, isLoading, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // 输入法组合状态（如中文/日文候选词选择）时不触发发送
      if (e.nativeEvent.isComposing || e.keyCode === 229)
        return
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const placeholder = isMobile ? t('placeholderShort') : t('placeholder')

  return (
    <div className="border-t bg-background px-3 py-3 sm:p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="relative flex-1">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="min-h-[44px] max-h-[200px] resize-none pr-4 text-base md:text-sm"
            rows={1}
            disabled={disabled}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = `${Math.min(target.scrollHeight, 200)}px`
            }}
          />
        </div>
        {isLoading
          ? (
              <Button
                size="icon"
                variant="destructive"
                onClick={onStop}
                className="size-[44px] shrink-0 rounded-xl"
              >
                <Square className="size-4" />
              </Button>
            )
          : (
              <Button
                size="icon"
                onClick={handleSend}
                disabled={!value.trim() || disabled}
                className="size-[44px] shrink-0 rounded-xl"
              >
                <ArrowUp className="size-4" />
              </Button>
            )}
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
        {tc('disclaimer')}
      </p>
    </div>
  )
}
