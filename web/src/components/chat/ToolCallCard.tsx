import { useState } from 'react'
import { ChevronDown, ChevronRight, Monitor, Wrench } from 'lucide-react'
import { FaApple, FaWindows, FaLinux, FaUbuntu, FaFedora, FaSuse, FaCentos, FaRedhat } from 'react-icons/fa6'
import { SiDebian, SiArchlinux, SiAlpinelinux, SiLinuxmint, SiManjaro } from 'react-icons/si'
import { Badge } from '@/components/ui/badge'
import type { ToolCall } from '@/types/chat'

interface DeviceMeta {
  device_name: string
  os_type: string
}

function OsIcon({ os, className }: { os: string, className?: string }) {
  const cls = className || 'size-3'
  switch (os) {
    case 'macos': return <FaApple className={cls} />
    case 'windows': return <FaWindows className={cls} />
    case 'ubuntu': return <FaUbuntu className={cls} />
    case 'debian': return <SiDebian className={cls} />
    case 'fedora': return <FaFedora className={cls} />
    case 'arch': return <SiArchlinux className={cls} />
    case 'centos': return <FaCentos className={cls} />
    case 'alpine': return <SiAlpinelinux className={cls} />
    case 'suse': return <FaSuse className={cls} />
    case 'manjaro': return <SiManjaro className={cls} />
    case 'mint': return <SiLinuxmint className={cls} />
    case 'redhat': return <FaRedhat className={cls} />
    case 'linux': return <FaLinux className={cls} />
    default: return <Monitor className={cls} />
  }
}

/** 从工具结果中解析设备信息 */
function parseDeviceInfo(result: string | undefined): { cleanResult: string, device: DeviceMeta | null } {
  if (!result) return { cleanResult: '', device: null }
  const match = result.match(/\n<!--device:(.+?)-->$/)
  if (!match) return { cleanResult: result, device: null }
  try {
    const data = JSON.parse(match[1]) as { _device: DeviceMeta }
    return { cleanResult: result.replace(match[0], ''), device: data._device }
  }
  catch {
    return { cleanResult: result, device: null }
  }
}

/** local_agent 相关工具名 */
const LOCAL_TOOLS = new Set(['local_run_command', 'local_read_file', 'local_write_file', 'local_list_files', 'local_list_devices'])

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

  const { cleanResult, device } = parseDeviceInfo(toolCall.result)
  const isLocalTool = LOCAL_TOOLS.has(toolCall.name)

  // 设备名称：优先从结果中解析，running 时 fallback 到 args.device
  const deviceLabel = device?.device_name || (isLocalTool && toolCall.args.device as string) || null
  const deviceOs = device?.os_type || null

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
        {/* 设备标识 */}
        {isLocalTool && deviceLabel && (
          <span className="ml-1.5 inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {deviceOs ? <OsIcon os={deviceOs} className="size-2.5" /> : <Monitor className="size-2.5" />}
            {deviceLabel}
          </span>
        )}
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
          {cleanResult && (
            <div>
              <p className="mb-1 font-medium text-muted-foreground">Result</p>
              <pre className="overflow-x-auto rounded bg-background p-2 text-[11px] leading-relaxed max-h-48">
                {cleanResult}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
