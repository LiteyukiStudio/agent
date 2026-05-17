import type { KeyboardEvent } from 'react'
import { ArrowUp, ImagePlus, Square, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

const MAX_IMAGE_SIZE_MB = 4
const MAX_IMAGE_COUNT = 4

interface ChatInputProps {
  onSend: (content: string, images?: File[]) => void
  onStop?: () => void
  isLoading: boolean
  disabled?: boolean
}

export function ChatInput({ onSend, onStop, isLoading, disabled }: ChatInputProps) {
  const { t } = useTranslation('chat')
  const { t: tc } = useTranslation('common')
  const [value, setValue] = useState('')
  const [attachedImages, setAttachedImages] = useState<File[]>([])
  const [previewUrls, setPreviewUrls] = useState<string[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const urls = attachedImages.map(file => URL.createObjectURL(file))
    setPreviewUrls(urls)
    return () => {
      for (const url of urls) {
        URL.revokeObjectURL(url)
      }
    }
  }, [attachedImages])

  const addImages = useCallback((files: File[]) => {
    const validFiles: File[] = []
    for (const file of files) {
      if (!file.type.startsWith('image/'))
        continue
      if (file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024) {
        toast.error(t('imageTooBig', { max: MAX_IMAGE_SIZE_MB }))
        continue
      }
      validFiles.push(file)
    }
    setAttachedImages((prev) => {
      const remaining = MAX_IMAGE_COUNT - prev.length
      if (remaining <= 0) {
        toast.error(t('imageLimitReached', { max: MAX_IMAGE_COUNT }))
        return prev
      }
      const toAdd = validFiles.slice(0, remaining)
      if (validFiles.length > remaining) {
        toast.error(t('imageLimitReached', { max: MAX_IMAGE_COUNT }))
      }
      return [...prev, ...toAdd]
    })
  }, [t])

  const removeImage = useCallback((index: number) => {
    setAttachedImages(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleSend = useCallback(() => {
    if ((!value.trim() && attachedImages.length === 0) || isLoading || disabled)
      return
    onSend(value, attachedImages.length > 0 ? attachedImages : undefined)
    setValue('')
    setAttachedImages([])
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value, attachedImages, isLoading, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.nativeEvent.isComposing || e.keyCode === 229)
        return
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const items = e.clipboardData.items
      const imageFiles: File[] = []
      for (let i = 0; i < items.length; i++) {
        const item = items[i]
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file)
            imageFiles.push(file)
        }
      }
      if (imageFiles.length > 0) {
        e.preventDefault()
        addImages(imageFiles)
      }
    },
    [addImages],
  )

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const placeholder = isMobile ? t('placeholderShort') : t('placeholder')

  return (
    <div className="border-t bg-background px-3 py-3 sm:p-4">
      <div className="mx-auto max-w-3xl">
        {attachedImages.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {attachedImages.map((file, i) => (
              <div key={`${file.name}-${i}`} className="group relative">
                <img
                  src={previewUrls[i]}
                  alt=""
                  className="size-16 rounded-lg border object-cover"
                />
                <button
                  type="button"
                  onClick={() => removeImage(i)}
                  className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <X className="size-3" />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files || [])
              if (files.length > 0)
                addImages(files)
              e.target.value = ''
            }}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-[48px] shrink-0 rounded-xl text-muted-foreground hover:text-foreground"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || attachedImages.length >= MAX_IMAGE_COUNT}
            title={t('attachImage')}
          >
            <ImagePlus className="size-5" />
          </Button>
          <div className="relative flex-1">
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              onDragOver={e => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                const files = Array.from(e.dataTransfer.files || [])
                if (files.length > 0)
                  addImages(files)
              }}
              placeholder={placeholder}
              className="min-h-[48px] max-h-[200px] resize-none py-3 pr-4 text-base leading-6"
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
                  className="size-[48px] shrink-0 rounded-xl"
                >
                  <Square className="size-4" />
                </Button>
              )
            : (
                <Button
                  size="icon"
                  onClick={handleSend}
                  disabled={(!value.trim() && attachedImages.length === 0) || disabled}
                  className="size-[48px] shrink-0 rounded-xl"
                >
                  <ArrowUp className="size-4" />
                </Button>
              )}
        </div>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          {tc('disclaimer')}
        </p>
      </div>
    </div>
  )
}
