import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AdminLayout } from '@/pages/admin/AdminLayout'
import { AdminUserSessionsPage } from '@/pages/admin/AdminUserSessionsPage'
import { OAuthPage } from '@/pages/admin/OAuthPage'
import { QuotaPage } from '@/pages/admin/QuotaPage'
import { UsersPage } from '@/pages/admin/UsersPage'
import { ChatPage } from '@/pages/ChatPage'
import { CliAuthPage } from '@/pages/CliAuthPage'
import { DeviceAuthPage } from '@/pages/DeviceAuthPage'
import { LoginPage } from '@/pages/LoginPage'
import { PublicSessionPage } from '@/pages/PublicSessionPage'
import { SettingsPage } from '@/pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" richColors closeButton />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* CLI / Device 授权页面 */}
        <Route path="/auth/cli" element={<CliAuthPage />} />
        <Route path="/device" element={<DeviceAuthPage />} />

        {/* Public session view (no auth required) */}
        <Route path="/session/:sessionId/public" element={<PublicSessionPage />} />

        {/* Chat routes */}
        <Route
          path="/"
          element={(
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          )}
        />
        <Route
          path="/session/:sessionId"
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
          <Route path="users/:userId/sessions" element={<AdminUserSessionsPage />} />
          <Route path="users/:userId/sessions/:sessionId" element={<AdminUserSessionsPage />} />
          <Route path="oauth" element={<OAuthPage />} />
          <Route path="quota" element={<QuotaPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
