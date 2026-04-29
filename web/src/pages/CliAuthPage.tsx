import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import { Bot, CheckCircle, Loader2, Monitor, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/hooks/useAuth'
import { apiPost } from '@/lib/api'

type Status = 'waiting' | 'authorizing' | 'success' | 'error'

export function CliAuthPage() {
  const { user, loading } = useAuth()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<Status>('waiting')
  const [error, setError] = useState('')

  const callbackUrl = searchParams.get('callback')
  const hostname = searchParams.get('hostname') || 'unknown'

  // If not logged in, redirect to login with return URL
  useEffect(() => {
    if (!loading && !user) {
      const currentUrl = window.location.href
      window.location.href = `/login?redirect=${encodeURIComponent(currentUrl)}`
    }
  }, [loading, user])

  async function handleApprove() {
    if (!callbackUrl) {
      setError('Missing callback URL')
      setStatus('error')
      return
    }

    setStatus('authorizing')

    try {
      const res = await apiPost<{ token: string }>('/api/v1/auth/device/cli-token', {
        hostname,
      })

      // Redirect to CLI's localhost callback with token
      window.location.href = `${callbackUrl}?token=${encodeURIComponent(res.token)}`
      setStatus('success')
    }
    catch (err) {
      setError(err instanceof Error ? err.message : 'Authorization failed')
      setStatus('error')
    }
  }

  function handleReject() {
    if (callbackUrl) {
      window.location.href = `${callbackUrl}?error=${encodeURIComponent('User rejected authorization')}`
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
          <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-emerald-100 dark:bg-emerald-900">
            <Monitor className="size-8 text-emerald-700 dark:text-emerald-300" />
          </div>
          <CardTitle className="text-xl">授权 Local Agent</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {status === 'waiting' && (
            <>
              <div className="rounded-lg border bg-muted/50 p-4 text-sm space-y-2">
                <div className="flex items-center gap-2">
                  <Bot className="size-4 text-muted-foreground" />
                  <span className="text-muted-foreground">主机名</span>
                  <span className="font-medium">{hostname}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="size-4" />
                  <span className="text-muted-foreground">用户</span>
                  <span className="font-medium">{user?.username}</span>
                </div>
              </div>

              <p className="text-sm text-muted-foreground text-center">
                Local Agent 请求访问你的账户。授权后它可以在你的电脑上执行命令和文件操作。
              </p>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={handleReject}
                >
                  拒绝
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleApprove}
                >
                  授权连接
                </Button>
              </div>
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
              <p className="text-sm font-medium">授权成功</p>
              <p className="text-xs text-muted-foreground">你可以关闭此页面，回到终端继续操作。</p>
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
