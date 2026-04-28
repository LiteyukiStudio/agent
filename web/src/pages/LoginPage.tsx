import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { Bot, Snowflake } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/useAuth'
import { apiGet } from '@/lib/api'

interface OAuthProvider {
  id: string
  name: string
  issuer_url: string
}

export function LoginPage() {
  const { t } = useTranslation('auth')
  const { t: tc } = useTranslation('common')
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [providers, setProviders] = useState<OAuthProvider[]>([])

  useEffect(() => {
    if (user)
      navigate('/', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    apiGet<OAuthProvider[]>('/api/v1/auth/providers')
      .then(setProviders)
      .catch(() => {})
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : t('loginFailed'))
    }
    finally {
      setLoading(false)
    }
  }

  function handleOAuth(providerId: string) {
    const base = import.meta.env.VITE_API_URL || ''
    window.location.href = `${base}/api/v1/auth/oauth/login/${providerId}`
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex size-12 items-center justify-center rounded-xl bg-emerald-100 dark:bg-emerald-900">
            <Snowflake className="size-6 text-emerald-700 dark:text-emerald-300" />
          </div>
          <CardTitle className="text-xl">{tc('appName')}</CardTitle>
          <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-3">
            <Input
              placeholder={t('username')}
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
            <Input
              type="password"
              placeholder={t('password')}
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? t('loggingIn') : t('login')}
            </Button>
          </form>

          {providers.length > 0 && (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">{tc('or')}</span>
                </div>
              </div>

              <div className="space-y-2">
                {providers.map(p => (
                  <Button
                    key={p.id}
                    variant="outline"
                    className="w-full gap-2"
                    onClick={() => handleOAuth(p.id)}
                  >
                    <Bot className="size-4" />
                    {t('loginWith', { provider: p.name })}
                  </Button>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
