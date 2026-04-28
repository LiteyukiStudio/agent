import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { LoginPage } from '@/pages/LoginPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { AdminLayout } from '@/pages/admin/AdminLayout'
import { UsersPage } from '@/pages/admin/UsersPage'
import { OAuthPage } from '@/pages/admin/OAuthPage'
import { QuotaPage } from '@/pages/admin/QuotaPage'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" richColors closeButton />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/"
          element={(
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          )}
        />

        <Route
          path="/settings"
          element={(
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          )}
        />

        <Route
          path="/admin"
          element={(
            <ProtectedRoute requireAdmin>
              <AdminLayout />
            </ProtectedRoute>
          )}
        >
          <Route index element={<Navigate to="/admin/users" replace />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="oauth" element={<OAuthPage />} />
          <Route path="quota" element={<QuotaPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
