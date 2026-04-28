import { useState } from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { ToolCall } from '@/types/chat'

interface ToolCallCardProps {
  toolCall: ToolCall
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false)

  const statusColor: Record<ToolCall['status'], string> = {
    pending: 'bg-muted text-muted-foreground',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    error: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  }

  return (
    <div className="my-1.5">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-colors hover:bg-accent ${expanded ? 'bg-accent' : ''}`}
      >
        {expanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        <Wrench className="size-3 text-muted-foreground" />
        <span className="font-medium">{toolCall.name}</span>
        <Badge variant="secondary" className={`ml-1 text-[10px] px-1.5 py-0 ${statusColor[toolCall.status]}`}>
          {toolCall.status}
        </Badge>
      </button>

      {expanded && (
        <div className="mt-1.5 ml-5 space-y-2 rounded-lg border bg-muted/50 p-3 text-xs">
          {Object.keys(toolCall.args).length > 0 && (
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Arguments</p>
              <pre className="overflow-x-auto rounded bg-background p-2 text-[11px] leading-relaxed">
                {JSON.stringify(toolCall.args, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.result && (
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Result</p>
              <pre className="overflow-x-auto rounded bg-background p-2 text-[11px] leading-relaxed max-h-48">
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
