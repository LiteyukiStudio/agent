import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Copy, Key, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
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
  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [usage, setUsage] = useState<UsageStats | null>(null)
  const [newTokenName, setNewTokenName] = useState('')
  const [createdToken, setCreatedToken] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleteTokenId, setDeleteTokenId] = useState<string | null>(null)

  const loadTokens = useCallback(() => {
    apiGet<ApiToken[]>('/api/v1/auth/tokens').then(setTokens).catch(() => {})
  }, [])

  const loadUsage = useCallback(() => {
    apiGet<UsageStats>('/api/v1/usage/me').then(setUsage).catch(() => {})
  }, [])

  useEffect(() => {
    loadTokens()
    loadUsage()
  }, [loadTokens, loadUsage])

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
      <h1 className="text-2xl font-bold">{t('title')}</h1>

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

          {tokens.length === 0 && (
            <p className="text-sm text-muted-foreground">{t('noTokens')}</p>
          )}

          {tokens.map(tok => (
            <div key={tok.id} className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <p className="text-sm font-medium">{tok.name}</p>
                <p className="text-xs text-muted-foreground">
                  {`lys_...${tok.token_last_eight}`}
                  {' '}
                  ·
                  {new Date(tok.created_at).toLocaleDateString()}
                </p>
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
