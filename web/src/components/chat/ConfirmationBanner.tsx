import { AlertTriangle, Check, CheckCheck, Lock, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiGet, apiPost } from '@/lib/api'

interface Confirmation {
  id: string
  tool: string
  args: Record<string, unknown>
  device_id: string
  device_name: string
  needs_password?: boolean
  timestamp: number
}

function ConfirmCard({ confirmation: c, onDone }: { confirmation: Confirmation, onDone: () => void }) {
  const [password, setPassword] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (c.needs_password && inputRef.current) {
      inputRef.current.focus()
    }
  }, [c.needs_password])

  async function handleApprove() {
    const body = password ? { password } : {}
    await apiPost(`/api/v1/local-agent/confirmations/${c.id}/approve`, body)
    onDone()
  }

  async function handleAlwaysApprove() {
    const body = password ? { password } : {}
    await apiPost(`/api/v1/local-agent/confirmations/${c.id}/always`, body)
    onDone()
  }

  async function handleReject() {
    await apiPost(`/api/v1/local-agent/confirmations/${c.id}/reject`, {})
    onDone()
  }

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-yellow-300 bg-yellow-50 p-3 shadow-sm dark:border-yellow-800 dark:bg-yellow-950/60">
      <div className="flex items-center gap-2 text-sm font-medium text-yellow-800 dark:text-yellow-200">
        <AlertTriangle className="size-4 shrink-0" />
        <span>需要确认操作</span>
        <span className="ml-auto text-[10px] text-yellow-600 dark:text-yellow-400">
          {c.device_name}
        </span>
      </div>
      <pre className="max-h-24 overflow-auto rounded bg-yellow-100/70 px-2 py-1.5 text-xs text-yellow-900 dark:bg-yellow-900/40 dark:text-yellow-100">
        {typeof c.args.command === 'string' ? c.args.command : JSON.stringify(c.args, null, 2)}
      </pre>

      {/* sudo 密码输入 */}
      {c.needs_password && (
        <div className="flex items-center gap-2">
          <Lock className="size-3.5 shrink-0 text-yellow-700 dark:text-yellow-300" />
          <Input
            ref={inputRef}
            type="password"
            placeholder="输入 sudo 密码"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && password)
                handleApprove()
            }}
            className="h-7 text-xs flex-1 border-yellow-300 dark:border-yellow-700"
          />
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          className="gap-1 text-xs border-yellow-300 text-yellow-800 hover:bg-yellow-100 dark:border-yellow-700 dark:text-yellow-200 dark:hover:bg-yellow-900/50"
          onClick={handleReject}
        >
          <X className="size-3" />
          拒绝
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="gap-1 text-xs border-yellow-400 text-yellow-800 hover:bg-yellow-100 dark:border-yellow-600 dark:text-yellow-200 dark:hover:bg-yellow-900/50"
          onClick={handleApprove}
          disabled={c.needs_password && !password}
        >
          <Check className="size-3" />
          允许
        </Button>
        <Button
          size="sm"
          className="gap-1 text-xs bg-yellow-500 hover:bg-yellow-600 text-white dark:bg-yellow-600 dark:hover:bg-yellow-700"
          onClick={handleAlwaysApprove}
          disabled={c.needs_password && !password}
          title="本次会话后续相同命令不再询问（含密码记忆）"
        >
          <CheckCheck className="size-3" />
          始终允许
        </Button>
      </div>
    </div>
  )
}

export function ConfirmationBanner() {
  const [confirmations, setConfirmations] = useState<Confirmation[]>([])

  const poll = useCallback(() => {
    apiGet<{ confirmations: Confirmation[] }>('/api/v1/local-agent/confirmations')
      .then(data => setConfirmations(data.confirmations))
      .catch(() => {})
  }, [])

  useEffect(() => {
    poll()
    const timer = setInterval(poll, 2000)
    return () => clearInterval(timer)
  }, [poll])

  if (confirmations.length === 0)
    return null

  return (
    <div className="flex flex-col gap-2">
      {confirmations.map(c => (
        <ConfirmCard
          key={c.id}
          confirmation={c}
          onDone={() => setConfirmations(prev => prev.filter(x => x.id !== c.id))}
        />
      ))}
    </div>
  )
}
