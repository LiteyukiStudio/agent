import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { apiDelete, apiGet, apiPost } from '@/lib/api'

interface OAuthProvider {
  id: string
  name: string
  issuer_url: string
  client_id: string
  enabled: boolean
  access_mode: string
  created_at: string
}

export function OAuthPage() {
  const { t: tc } = useTranslation('common')
  const [providers, setProviders] = useState<OAuthProvider[]>([])
  const [form, setForm] = useState({ name: '', issuer_url: '', client_id: '', client_secret: '' })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const load = useCallback(() => {
    apiGet<OAuthProvider[]>('/api/v1/admin/oauth-providers').then(setProviders).catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  async function handleCreate() {
    try {
      await apiPost('/api/v1/admin/oauth-providers', form)
      setForm({ name: '', issuer_url: '', client_id: '', client_secret: '' })
      setDialogOpen(false)
      load()
      toast.success('Provider created')
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create provider')
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteId)
      return
    try {
      await apiDelete(`/api/v1/admin/oauth-providers/${deleteId}`)
      setDeleteId(null)
      load()
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete provider')
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">OAuth Providers</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus className="mr-1 size-4" />
                Add Provider
              </Button>
            }
          />
          <DialogContent>
            <DialogTitle>Add OAuth Provider</DialogTitle>
            <DialogDescription>Enter the OIDC issuer URL and client credentials.</DialogDescription>
            <div className="space-y-3 py-4">
              <Input placeholder="Display name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              <Input placeholder="Issuer URL (e.g. https://git.example.com)" value={form.issuer_url} onChange={e => setForm(f => ({ ...f, issuer_url: e.target.value }))} />
              <Input placeholder="Client ID" value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} />
              <Input placeholder="Client Secret" type="password" value={form.client_secret} onChange={e => setForm(f => ({ ...f, client_secret: e.target.value }))} />
            </div>
            <DialogFooter>
              <DialogClose
                render={<Button variant="outline">{tc('cancel')}</Button>}
              />
              <Button onClick={handleCreate} disabled={!form.name || !form.issuer_url || !form.client_id}>
                {tc('create')}
              </Button>
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
                <TableHead>Issuer</TableHead>
                <TableHead>Access Mode</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {providers.map(p => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell className="max-w-[200px] truncate text-muted-foreground">{p.issuer_url}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{p.access_mode}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={p.enabled ? 'default' : 'secondary'}>
                      {p.enabled ? tc('enabled') : tc('disabled')}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteId(p.id)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {providers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    {tc('noData')}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

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
