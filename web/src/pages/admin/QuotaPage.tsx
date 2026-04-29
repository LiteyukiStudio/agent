import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { useTitle } from '@/hooks/useTitle'
import { apiDelete, apiGet, apiPatch, apiPost } from '@/lib/api'

interface QuotaPlan {
  id: string
  name: string
  daily_tokens: number | null
  weekly_tokens: number | null
  monthly_tokens: number | null
  requests_per_minute: number
  is_default: boolean
}

function formatTokens(n: number | null): string {
  if (n === null)
    return 'Unlimited'
  if (n >= 1_000_000)
    return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000)
    return `${(n / 1000).toFixed(0)}k`
  return String(n)
}

export function QuotaPage() {
  const { t: tc } = useTranslation('common')
  useTitle('Quota Plans')
  const [plans, setPlans] = useState<QuotaPlan[]>([])
  const [form, setForm] = useState({ name: '', daily_tokens: '', weekly_tokens: '', monthly_tokens: '', requests_per_minute: '10' })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editPlan, setEditPlan] = useState<QuotaPlan | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', daily_tokens: '', weekly_tokens: '', monthly_tokens: '', requests_per_minute: '' })
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const load = useCallback(() => {
    apiGet<QuotaPlan[]>('/api/v1/admin/quota-plans').then(setPlans).catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  async function handleCreate() {
    try {
      await apiPost('/api/v1/admin/quota-plans', {
        name: form.name,
        daily_tokens: form.daily_tokens ? Number(form.daily_tokens) : null,
        weekly_tokens: form.weekly_tokens ? Number(form.weekly_tokens) : null,
        monthly_tokens: form.monthly_tokens ? Number(form.monthly_tokens) : null,
        requests_per_minute: Number(form.requests_per_minute) || 10,
        is_default: false,
      })
      setForm({ name: '', daily_tokens: '', weekly_tokens: '', monthly_tokens: '', requests_per_minute: '10' })
      setDialogOpen(false)
      load()
      toast.success('Plan created')
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create plan')
    }
  }

  function openEdit(plan: QuotaPlan) {
    setEditPlan(plan)
    setEditForm({
      name: plan.name,
      daily_tokens: plan.daily_tokens !== null ? String(plan.daily_tokens) : '',
      weekly_tokens: plan.weekly_tokens !== null ? String(plan.weekly_tokens) : '',
      monthly_tokens: plan.monthly_tokens !== null ? String(plan.monthly_tokens) : '',
      requests_per_minute: String(plan.requests_per_minute),
    })
    setEditDialogOpen(true)
  }

  async function handleEdit() {
    if (!editPlan)
      return
    try {
      await apiPatch(`/api/v1/admin/quota-plans/${editPlan.id}`, {
        name: editForm.name || undefined,
        daily_tokens: editForm.daily_tokens ? Number(editForm.daily_tokens) : null,
        weekly_tokens: editForm.weekly_tokens ? Number(editForm.weekly_tokens) : null,
        monthly_tokens: editForm.monthly_tokens ? Number(editForm.monthly_tokens) : null,
        requests_per_minute: editForm.requests_per_minute ? Number(editForm.requests_per_minute) : undefined,
      })
      setEditDialogOpen(false)
      setEditPlan(null)
      load()
      toast.success('Plan updated')
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update plan')
    }
  }

  async function handleSetDefault(id: string) {
    try {
      await apiPatch(`/api/v1/admin/quota-plans/${id}`, { is_default: true })
      load()
      toast.success('Default plan updated')
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to set default')
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteId)
      return
    try {
      await apiDelete(`/api/v1/admin/quota-plans/${deleteId}`)
      setDeleteId(null)
      load()
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete plan')
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Quota Plans</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus className="mr-1 size-4" />
                Add Plan
              </Button>
            }
          />
          <DialogContent>
            <DialogTitle>Create Quota Plan</DialogTitle>
            <DialogDescription>Leave token fields empty for unlimited.</DialogDescription>
            <div className="space-y-3 py-4">
              <Input placeholder="Plan name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              <Input placeholder="Daily tokens (empty = unlimited)" type="number" value={form.daily_tokens} onChange={e => setForm(f => ({ ...f, daily_tokens: e.target.value }))} />
              <Input placeholder="Weekly tokens" type="number" value={form.weekly_tokens} onChange={e => setForm(f => ({ ...f, weekly_tokens: e.target.value }))} />
              <Input placeholder="Monthly tokens" type="number" value={form.monthly_tokens} onChange={e => setForm(f => ({ ...f, monthly_tokens: e.target.value }))} />
              <Input placeholder="Requests per minute" type="number" value={form.requests_per_minute} onChange={e => setForm(f => ({ ...f, requests_per_minute: e.target.value }))} />
            </div>
            <DialogFooter>
              <DialogClose
                render={<Button variant="outline">{tc('cancel')}</Button>}
              />
              <Button onClick={handleCreate} disabled={!form.name}>{tc('create')}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Daily</TableHead>
                <TableHead>Weekly</TableHead>
                <TableHead>Monthly</TableHead>
                <TableHead>RPM</TableHead>
                <TableHead>Default</TableHead>
                <TableHead className="w-40" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {plans.map(p => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell>{formatTokens(p.daily_tokens)}</TableCell>
                  <TableCell>{formatTokens(p.weekly_tokens)}</TableCell>
                  <TableCell>{formatTokens(p.monthly_tokens)}</TableCell>
                  <TableCell>{p.requests_per_minute}</TableCell>
                  <TableCell>
                    {p.is_default
                      ? <Badge>Default</Badge>
                      : (
                          <Button variant="ghost" size="sm" onClick={() => handleSetDefault(p.id)}>
                            Set default
                          </Button>
                        )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEdit(p)}
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteId(p.id)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {plans.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
                    {tc('noData')}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogTitle>Edit Quota Plan</DialogTitle>
          <DialogDescription>Modify the plan limits. Leave empty for unlimited.</DialogDescription>
          <div className="space-y-3 py-4">
            <Input placeholder="Plan name" value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} />
            <Input placeholder="Daily tokens (empty = unlimited)" type="number" value={editForm.daily_tokens} onChange={e => setEditForm(f => ({ ...f, daily_tokens: e.target.value }))} />
            <Input placeholder="Weekly tokens" type="number" value={editForm.weekly_tokens} onChange={e => setEditForm(f => ({ ...f, weekly_tokens: e.target.value }))} />
            <Input placeholder="Monthly tokens" type="number" value={editForm.monthly_tokens} onChange={e => setEditForm(f => ({ ...f, monthly_tokens: e.target.value }))} />
            <Input placeholder="Requests per minute" type="number" value={editForm.requests_per_minute} onChange={e => setEditForm(f => ({ ...f, requests_per_minute: e.target.value }))} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>{tc('cancel')}</Button>
            <Button onClick={handleEdit} disabled={!editForm.name}>{tc('save')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteId}
        onOpenChange={open => !open && setDeleteId(null)}
        title={tc('confirmDelete')}
        description={tc('confirmDeleteDesc')}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  )
}
