import { CheckCircle, Key, Loader2, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/hooks/useAuth'
import { apiPost } from '@/lib/api'

type Status = 'waiting' | 'authorizing' | 'success' | 'error'

export function DeviceAuthPage() {
  const { user, loading } = useAuth()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<Status>('waiting')
  const [error, setError] = useState('')

  const userCode = searchParams.get('code') || ''

  // If not logged in, redirect to login
  if (!loading && !user) {
    const currentUrl = window.location.href
    window.location.href = `/login?redirect=${encodeURIComponent(currentUrl)}`
    return null
  }

  async function handleApprove() {
    if (!userCode) {
      setError('Missing verification code')
      setStatus('error')
      return
    }

    setStatus('authorizing')
    try {
      await apiPost('/api/v1/auth/device/approve', { user_code: userCode })
      setStatus('success')
    }
    catch (err) {
      setError(err instanceof Error ? err.message : 'Authorization failed')
      setStatus('error')
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-blue-100 dark:bg-blue-900">
            <Key className="size-8 text-blue-700 dark:text-blue-300" />
          </div>
          <CardTitle className="text-xl">设备验证</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {status === 'waiting' && (
            <>
              <div className="rounded-lg border bg-muted/50 p-6 text-center">
                <p className="text-sm text-muted-foreground mb-2">验证码</p>
                <p className="text-3xl font-mono font-bold tracking-widest">{userCode}</p>
              </div>

              <p className="text-sm text-muted-foreground text-center">
                请确认终端中显示的验证码与上方一致，然后点击授权。
              </p>

              <Button className="w-full" onClick={handleApprove}>
                确认授权
              </Button>
            </>
          )}

          {status === 'authorizing' && (
            <div className="flex flex-col items-center gap-3 py-4">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在授权...</p>
            </div>
          )}

          {status === 'success' && (
            <div className="flex flex-col items-center gap-3 py-4">
              <CheckCircle className="size-8 text-emerald-500" />
              <p className="text-sm font-medium">授权成功！</p>
              <p className="text-xs text-muted-foreground">终端将自动完成连接，你可以关闭此页面。</p>
            </div>
          )}

          {status === 'error' && (
            <div className="flex flex-col items-center gap-3 py-4">
              <XCircle className="size-8 text-destructive" />
              <p className="text-sm font-medium">授权失败</p>
              <p className="text-xs text-muted-foreground">{error}</p>
              <Button variant="outline" size="sm" onClick={() => setStatus('waiting')}>
                重试
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
