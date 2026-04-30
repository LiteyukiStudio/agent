import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAuth } from '@/hooks/useAuth'
import { useTitle } from '@/hooks/useTitle'
import { apiGet, apiPatch } from '@/lib/api'

interface UserItem {
  id: string
  username: string
  email: string | null
  role: string
  quota_plan_id: string | null
}

interface QuotaPlan {
  id: string
  name: string
  is_default: boolean
}

interface UsageStats {
  total_users: number
  total_tokens_today: number
  total_tokens_this_month: number
  total_records: number
}

function formatTokens(n: number): string {
  if (n >= 1_000_000)
    return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000)
    return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export function UsersPage() {
  const { user: me } = useAuth()
  useTitle('Users')
  const [users, setUsers] = useState<UserItem[]>([])
  const [stats, setStats] = useState<UsageStats | null>(null)
  const [plans, setPlans] = useState<QuotaPlan[]>([])

  const loadUsers = useCallback(() => {
    apiGet<UserItem[]>('/api/v1/admin/users').then(setUsers).catch(() => {})
  }, [])

  const loadPlans = useCallback(() => {
    apiGet<QuotaPlan[]>('/api/v1/admin/quota-plans').then(setPlans).catch(() => {})
  }, [])

  useEffect(() => {
    loadUsers()
    loadPlans()
    apiGet<UsageStats>('/api/v1/admin/usage/stats').then(setStats).catch(() => {})
  }, [loadUsers, loadPlans])

  async function handleRoleChange(userId: string, role: string) {
    try {
      await apiPatch(`/api/v1/admin/users/${userId}`, { role })
      loadUsers()
      toast.success('Role updated')
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update role')
    }
  }

  async function handleQuotaChange(userId: string, planId: string | null) {
    try {
      await apiPatch(`/api/v1/admin/users/${userId}/quota`, { quota_plan_id: planId })
      loadUsers()
      toast.success('Quota plan updated')
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update quota plan')
    }
  }

  function getPlanName(planId: string | null): string {
    if (!planId) {
      const defaultPlan = plans.find(p => p.is_default)
      return defaultPlan ? `${defaultPlan.name} (default)` : 'None'
    }
    const plan = plans.find(p => p.id === planId)
    return plan ? plan.name : 'Unknown'
  }

  const isSuperuser = me?.role === 'superuser'

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Users</h1>

      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total Users', value: stats.total_users },
            { label: 'Tokens Today', value: formatTokens(stats.total_tokens_today) },
            { label: 'Tokens This Month', value: formatTokens(stats.total_tokens_this_month) },
            { label: 'Total Records', value: stats.total_records },
          ].map(s => (
            <Card key={s.label}>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground">{s.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{s.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Quota Plan</TableHead>
                <TableHead className="w-48">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map(u => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.username}</TableCell>
                  <TableCell className="text-muted-foreground">{u.email || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'superuser' ? 'default' : u.role === 'admin' ? 'secondary' : 'outline'}>
                      {u.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {getPlanName(u.quota_plan_id)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {u.role !== 'superuser' && u.id !== me?.id && (
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            render={<Button variant="outline" size="sm">Role</Button>}
                          />
                          <DropdownMenuContent>
                            <DropdownMenuItem onClick={() => handleRoleChange(u.id, 'user')}>
                              User
                            </DropdownMenuItem>
                            {isSuperuser && (
                              <DropdownMenuItem onClick={() => handleRoleChange(u.id, 'admin')}>
                                Admin
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={<Button variant="outline" size="sm">Quota</Button>}
                        />
                        <DropdownMenuContent>
                          <DropdownMenuItem onClick={() => handleQuotaChange(u.id, null)}>
                            Use default
                          </DropdownMenuItem>
                          {plans.map(p => (
                            <DropdownMenuItem key={p.id} onClick={() => handleQuotaChange(u.id, p.id)}>
                              {p.name}
                              {p.is_default && ' (default)'}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
