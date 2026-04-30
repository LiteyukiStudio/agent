import { Copy, Info, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useTitle } from '@/hooks/useTitle'
import { apiDelete, apiGet, apiPatch, apiPost } from '@/lib/api'

interface OAuthProvider {
  id: string
  name: string
  issuer_url: string
  client_id: string
  enabled: boolean
  access_mode: string
  allowed_groups: string
  callback_url: string | null
  created_at: string
}

const emptyForm = {
  name: '',
  issuer_url: '',
  client_id: '',
  client_secret: '',
  access_mode: 'whitelist',
  allowed_groups: '',
}

export function OAuthPage() {
  const { t: tc } = useTranslation('common')
  useTitle('OAuth Providers')
  const [providers, setProviders] = useState<OAuthProvider[]>([])
  const [form, setForm] = useState({ ...emptyForm })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const load = useCallback(() => {
    apiGet<OAuthProvider[]>('/api/v1/admin/oauth-providers').then(setProviders).catch(() => {})
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    setForm({ ...emptyForm })
    setEditingId(null)
    setDialogOpen(true)
  }

  function openEdit(p: OAuthProvider) {
    setForm({
      name: p.name,
      issuer_url: p.issuer_url,
      client_id: p.client_id,
      client_secret: '',
      access_mode: p.access_mode,
      allowed_groups: p.allowed_groups || '',
    })
    setEditingId(p.id)
    setDialogOpen(true)
  }

  async function handleSave() {
    try {
      if (editingId) {
        // Update: only send changed fields
        const body: Record<string, unknown> = {
          name: form.name,
          access_mode: form.access_mode,
          allowed_groups: form.allowed_groups,
        }
        if (form.issuer_url)
          body.issuer_url = form.issuer_url
        if (form.client_id)
          body.client_id = form.client_id
        if (form.client_secret)
          body.client_secret = form.client_secret
        await apiPatch(`/api/v1/admin/oauth-providers/${editingId}`, body)
        toast.success('Provider updated')
      }
      else {
        await apiPost('/api/v1/admin/oauth-providers', form)
        toast.success('Provider created')
      }
      setForm({ ...emptyForm })
      setDialogOpen(false)
      setEditingId(null)
      load()
    }
    catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save provider')
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

  const isBlacklist = form.access_mode === 'blacklist'

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">OAuth Providers</h1>
        <Button onClick={openCreate}>
          <Plus className="mr-1 size-4" />
          Add Provider
        </Button>
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogTitle>{editingId ? 'Edit Provider' : 'Add OAuth Provider'}</DialogTitle>
          <DialogDescription>
            {editingId
              ? 'Update the provider settings. Leave secret empty to keep unchanged.'
              : 'Enter the OIDC issuer URL and client credentials.'}
          </DialogDescription>
          <div className="space-y-3 py-4">
            <Input placeholder="Display name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            <Input placeholder="Issuer URL (e.g. https://auth.example.com)" value={form.issuer_url} onChange={e => setForm(f => ({ ...f, issuer_url: e.target.value }))} />
            <Input placeholder="Client ID" value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} />
            <Input placeholder={editingId ? 'Client Secret (leave empty to keep)' : 'Client Secret'} type="password" value={form.client_secret} onChange={e => setForm(f => ({ ...f, client_secret: e.target.value }))} />

            {/* Separator */}
            <div className="border-t pt-3">
              <p className="mb-2 text-sm font-medium">Access Control (OIDC Groups)</p>

              {/* Access Mode Toggle */}
              <label className="flex cursor-pointer items-center gap-3">
                <button
                  type="button"
                  role="switch"
                  aria-checked={isBlacklist}
                  onClick={() => setForm(f => ({ ...f, access_mode: isBlacklist ? 'whitelist' : 'blacklist' }))}
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${isBlacklist ? 'bg-destructive' : 'bg-primary'}`}
                >
                  <span className={`inline-block size-4 rounded-full bg-white transition-transform ${isBlacklist ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
                <span className="text-sm">
                  {isBlacklist ? 'Blacklist mode (listed groups are blocked)' : 'Whitelist mode (only listed groups allowed)'}
                </span>
              </label>

              {/* Groups Input */}
              <Input
                className="mt-2"
                placeholder="Allowed groups (comma separated, e.g. admin,dev-team)"
                value={form.allowed_groups}
                onChange={e => setForm(f => ({ ...f, allowed_groups: e.target.value }))}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                {isBlacklist
                  ? 'Users in these OIDC groups will be blocked from logging in.'
                  : 'Leave empty to allow all users. Fill in to restrict access to these groups only.'}
              </p>
            </div>

            {!editingId && (
              <div className="flex items-start gap-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                <span>Callback URL will be generated after creation. Set it in your OAuth app as the redirect URI.</span>
              </div>
            )}
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline">{tc('cancel')}</Button>} />
            <Button onClick={handleSave} disabled={!form.name || (!editingId && (!form.issuer_url || !form.client_id))}>
              {editingId ? tc('save') : tc('create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Issuer</TableHead>
                <TableHead>Callback URL</TableHead>
                <TableHead>Access</TableHead>
                <TableHead>Groups</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {providers.map(p => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell className="max-w-[180px] truncate text-muted-foreground">{p.issuer_url}</TableCell>
                  <TableCell>
                    {p.callback_url && (
                      <div className="flex items-center gap-1">
                        <code className="max-w-[180px] truncate text-xs text-muted-foreground">{p.callback_url}</code>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-6 shrink-0"
                          onClick={() => {
                            navigator.clipboard.writeText(p.callback_url!)
                            toast.success('Callback URL copied')
                          }}
                        >
                          <Copy className="size-3" />
                        </Button>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={p.access_mode === 'blacklist' ? 'destructive' : 'outline'}>
                      {p.access_mode}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="max-w-[150px] truncate text-xs text-muted-foreground">
                      {p.allowed_groups || '-'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={p.enabled ? 'default' : 'secondary'}>
                      {p.enabled ? tc('enabled') : tc('disabled')}
                    </Badge>
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
              {providers.length === 0 && (
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
