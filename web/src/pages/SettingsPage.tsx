import { ArrowLeft, Copy, Key, Monitor, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FaApple, FaCentos, FaFedora, FaLinux, FaRedhat, FaSuse, FaUbuntu, FaWindows } from 'react-icons/fa6'
import { SiAlpinelinux, SiArchlinux, SiDebian, SiLinuxmint, SiManjaro } from 'react-icons/si'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Input } from '@/components/ui/input'
import { useTitle } from '@/hooks/useTitle'
import { apiDelete, apiGet, apiPost } from '@/lib/api'

interface ApiToken {
  id: string
  name: string
  token_last_eight: string
  scopes: string
  created_at: string
}

interface UsageStats {
  plan_name: string | null
  daily: { used: number, limit: number | null, remaining: number | null }
  weekly: { used: number, limit: number | null, remaining: number | null }
  monthly: { used: number, limit: number | null, remaining: number | null }
}

interface DevicesResponse {
  devices: { id: string, device_id: string, device_name: string, os_type: string, online: boolean, last_seen_at: string | null }[]
  count: number
}

function OsIcon({ os, className }: { os: string, className?: string }) {
  const cls = className || 'size-4'
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

function formatTokens(n: number): string {
  if (n >= 1_000_000)
    return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000)
    return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export function SettingsPage() {
  const { t } = useTranslation('settings')
  const { t: tc } = useTranslation('common')
  const navigate = useNavigate()
  useTitle('Settings')
  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [usage, setUsage] = useState<UsageStats | null>(null)
  const [newTokenName, setNewTokenName] = useState('')
  const [createdToken, setCreatedToken] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleteTokenId, setDeleteTokenId] = useState<string | null>(null)
  const [devices, setDevices] = useState<DevicesResponse | null>(null)

  const loadTokens = useCallback(() => {
    apiGet<ApiToken[]>('/api/v1/auth/tokens').then(setTokens).catch(() => {})
  }, [])

  const loadUsage = useCallback(() => {
    apiGet<UsageStats>('/api/v1/usage/me').then(setUsage).catch(() => {})
  }, [])

  const loadDevices = useCallback(() => {
    apiGet<DevicesResponse>('/api/v1/local-agent/devices').then(setDevices).catch(() => {})
  }, [])

  useEffect(() => {
    loadTokens()
    loadUsage()
    loadDevices()
    // 设备列表 5s 自动刷新
    const interval = setInterval(loadDevices, 5000)
    return () => clearInterval(interval)
  }, [loadTokens, loadUsage, loadDevices])

  async function handleCreate() {
    if (!newTokenName.trim())
      return
    setCreating(true)
    try {
      const res = await apiPost<{ token: string }>('/api/v1/auth/tokens', { name: newTokenName.trim(), scopes: '*' })
      setCreatedToken(res.token)
      setNewTokenName('')
      loadTokens()
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create token')
    }
    finally {
      setCreating(false)
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTokenId)
      return
    try {
      await apiDelete(`/api/v1/auth/tokens/${deleteTokenId}`)
      setDeleteTokenId(null)
      loadTokens()
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete token')
    }
  }

  function copyToken() {
    if (createdToken) {
      navigator.clipboard.writeText(createdToken)
      toast.success(t('tokenCopied'))
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      {/* 返回主页导航 */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="size-9 shrink-0"
          onClick={() => navigate('/')}
        >
          <ArrowLeft className="size-5" />
        </Button>
        <h1 className="text-2xl font-bold">{t('title')}</h1>
      </div>

      {/* Usage */}
      {usage && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('usage')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-muted-foreground">
              {t('plan')}
              :
              {' '}
              <Badge variant="secondary">{usage.plan_name || tc('noData')}</Badge>
            </p>
            <div className="grid grid-cols-3 gap-4">
              {(['daily', 'weekly', 'monthly'] as const).map(period => (
                <div key={period} className="rounded-lg bg-muted p-3">
                  <p className="text-xs text-muted-foreground">{t(period)}</p>
                  <p className="text-lg font-semibold">{formatTokens(usage[period].used)}</p>
                  <p className="text-xs text-muted-foreground">
                    {usage[period].limit ? `/ ${formatTokens(usage[period].limit!)}` : tc('unlimited')}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Online Devices */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Monitor className="size-4" />
              Local Agent 设备
            </span>
            <Button variant="ghost" size="icon" className="size-8" onClick={loadDevices}>
              <RefreshCw className="size-3.5" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {devices && devices.count > 0
            ? (
                <div className="space-y-2">
                  {devices.devices.map(d => (
                    <div key={d.device_id} className="flex items-center justify-between rounded-lg border p-3">
                      <div className="flex items-center gap-3">
                        <div className={`flex size-8 items-center justify-center rounded-lg ${d.online ? 'bg-emerald-100 dark:bg-emerald-900' : 'bg-muted'}`}>
                          <OsIcon os={d.os_type} className={`size-4 ${d.online ? 'text-emerald-700 dark:text-emerald-300' : 'text-muted-foreground'}`} />
                        </div>
                        <div>
                          <p className={`text-sm font-medium ${!d.online ? 'text-muted-foreground' : ''}`}>{d.device_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {d.device_id.slice(0, 8)}
                            {!d.online && d.last_seen_at && ` · 最后在线 ${new Date(d.last_seen_at).toLocaleString()}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={d.online ? 'default' : 'secondary'} className={d.online ? 'bg-emerald-500 hover:bg-emerald-500' : ''}>
                          {d.online ? '在线' : '离线'}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 text-destructive hover:text-destructive"
                          onClick={async () => {
                            try {
                              await apiDelete(`/api/v1/local-agent/devices/${d.device_id}`)
                              loadDevices()
                              loadTokens()
                              toast.success('设备已移除')
                            }
                            catch (err) {
                              toast.error(err instanceof Error ? err.message : 'Failed')
                            }
                          }}
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )
            : (
                <div className="text-center py-6 text-sm text-muted-foreground">
                  <Monitor className="mx-auto mb-2 size-8 text-muted-foreground/40" />
                  <p>暂无设备</p>
                  <p className="mt-1 text-xs">
                    安装
                    {' '}
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs">liteyuki-local-agent</code>
                    {' '}
                    并运行
                    {' '}
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs">liteyuki-agent</code>
                    {' '}
                    连接
                  </p>
                </div>
              )}
        </CardContent>
      </Card>

      {/* Created token alert */}
      {createdToken && (
        <Card className="border-emerald-500 bg-emerald-50 dark:bg-emerald-950">
          <CardContent className="pt-4">
            <p className="mb-2 text-sm font-medium">{t('tokenCreated')}</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded bg-background p-2 text-xs">{createdToken}</code>
              <Button variant="outline" size="icon" onClick={copyToken}>
                <Copy className="size-4" />
              </Button>
            </div>
            <Button variant="ghost" size="sm" className="mt-2" onClick={() => setCreatedToken(null)}>
              {tc('dismiss')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* API Tokens */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Key className="size-4" />
            {t('apiTokens')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder={t('tokenNamePlaceholder')}
              value={newTokenName}
              onChange={e => setNewTokenName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
            />
            <Button onClick={handleCreate} disabled={creating || !newTokenName.trim()}>
              <Plus className="mr-1 size-4" />
              {tc('create')}
            </Button>
          </div>

          {tokens.filter(tok => tok.scopes !== 'local-agent').length === 0 && (
            <p className="text-sm text-muted-foreground">{t('noTokens')}</p>
          )}

          {tokens.filter(tok => tok.scopes !== 'local-agent').map(tok => (
            <div key={tok.id} className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex items-center gap-2">
                <div>
                  <p className="text-sm font-medium">{tok.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {`lys_...${tok.token_last_eight}`}
                    {' '}
                    ·
                    {new Date(tok.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive"
                onClick={() => setDeleteTokenId(tok.id)}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* 吊销令牌确认 */}
      <ConfirmDialog
        open={!!deleteTokenId}
        onOpenChange={open => !open && setDeleteTokenId(null)}
        title={tc('confirmDelete')}
        description={tc('confirmRevokeToken')}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  )
}
