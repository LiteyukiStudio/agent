import type { ToolCall } from '@/types/chat'
import { AlertCircle, ChevronDown, ChevronRight, Monitor, Wrench } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FaApple, FaCentos, FaFedora, FaLinux, FaRedhat, FaSuse, FaUbuntu, FaWindows } from 'react-icons/fa6'
import { SiAlpinelinux, SiArchlinux, SiDebian, SiLinuxmint, SiManjaro } from 'react-icons/si'
import { Badge } from '@/components/ui/badge'

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
  if (!result)
    return { cleanResult: '', device: null }
  const match = result.match(/\n<!--device:(.+?)-->$/)
  if (!match)
    return { cleanResult: result, device: null }
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
  const [expanded, setExpanded] = useState(toolCall.status === 'error')
  const { t } = useTranslation('chat')

  // 工具出错时自动展开显示错误详情
  useEffect(() => {
    if (toolCall.status === 'error') {
      setExpanded(true) // eslint-disable-line react/set-state-in-effect
    }
  }, [toolCall.status])

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
    <div className="my-1.5 max-w-full">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-colors hover:bg-accent max-w-full overflow-x-auto scrollbar-none whitespace-nowrap ${expanded ? 'bg-accent' : ''} ${toolCall.status === 'error' ? 'border-red-200 dark:border-red-800' : ''}`}
      >
        {expanded ? <ChevronDown className="size-3 shrink-0" /> : <ChevronRight className="size-3 shrink-0" />}
        {toolCall.status === 'error'
          ? <AlertCircle className="size-3 shrink-0 text-red-500" />
          : <Wrench className="size-3 shrink-0 text-muted-foreground" />}
        <span className="font-medium">{toolCall.name}</span>
        <Badge variant="secondary" className={`text-[10px] px-1.5 py-0 shrink-0 ${statusColor[toolCall.status]}`}>
          {t(`toolStatus.${toolCall.status}`)}
        </Badge>
        {/* 设备标识 */}
        {isLocalTool && deviceLabel && (
          <span className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground shrink-0">
            {deviceOs ? <OsIcon os={deviceOs} className="size-2.5 shrink-0" /> : <Monitor className="size-2.5 shrink-0" />}
            <span>{deviceLabel}</span>
          </span>
        )}
      </button>

      {expanded && (
        <div className={`mt-1.5 ml-5 space-y-2 rounded-lg border p-3 text-xs max-w-full overflow-hidden ${toolCall.status === 'error' ? 'border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/30' : 'bg-muted/50'}`}>
          {Object.keys(toolCall.args).length > 0 && (
            <div className="overflow-hidden">
              <p className="mb-1 font-medium text-muted-foreground">Arguments</p>
              <pre className="overflow-x-auto rounded bg-background p-2 text-[11px] leading-relaxed max-w-full">
                {JSON.stringify(toolCall.args, null, 2)}
              </pre>
            </div>
          )}
          {cleanResult && (
            <div className="overflow-hidden">
              <p className={`mb-1 font-medium ${toolCall.status === 'error' ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}`}>
                {toolCall.status === 'error' ? 'Error' : 'Result'}
              </p>
              <pre className={`overflow-x-auto rounded p-2 text-[11px] leading-relaxed max-h-48 max-w-full ${toolCall.status === 'error' ? 'bg-red-100/50 text-red-700 dark:bg-red-950/50 dark:text-red-300' : 'bg-background'}`}>
                {cleanResult}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
