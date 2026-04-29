import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useTitle } from '@/hooks/useTitle'
import { Sidebar } from '@/components/chat/Sidebar'
import { ChatArea } from '@/components/chat/ChatArea'
import { useChat } from '@/hooks/useChat'

export function ChatPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const {
    sessions, activeSession, isLoading,
    setActiveSession, createSession, deleteSession,
    renameSession, sendMessage, togglePublic,
  } = useChat()
  const [mobileOpen, setMobileOpen] = useState(false)

  useTitle(activeSession?.title || 'Chat')

  // URL → state: URL 中的 sessionId 变化时，同步到 activeSession
  useEffect(() => {
    if (sessionId && sessionId !== activeSession?.id) {
      setActiveSession(sessionId)
    }
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  // 首页 / 无 sessionId 时，自动跳转到第一个会话
  useEffect(() => {
    if (!sessionId && sessions.length > 0) {
      navigate(`/session/${sessions[0].id}`, { replace: true })
    }
  }, [sessionId, sessions.length]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleSelectSession(id: string) {
    navigate(`/session/${id}`)
    setMobileOpen(false)
  }

  async function handleNewSession() {
    const newSession = await createSession()
    if (newSession) {
      navigate(`/session/${newSession.id}`)
    }
    setMobileOpen(false)
  }

  function handleDeleteSession(id: string) {
    deleteSession(id)
    if (activeSession?.id === id) {
      // 删除当前会话后，跳转到首页（会自动选第一个）
      navigate('/', { replace: true })
    }
  }

  const sidebarContent = (
    <Sidebar
      sessions={sessions}
      activeSessionId={activeSession?.id ?? null}
      isLoading={isLoading}
      onSelectSession={handleSelectSession}
      onNewSession={handleNewSession}
      onDeleteSession={handleDeleteSession}
      onRenameSession={renameSession}
    />
  )

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <div className="hidden md:block">
        {sidebarContent}
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger
          render={
            <Button
              variant="ghost"
              size="icon"
              className="fixed top-3 left-3 z-40 md:hidden"
            />
          }
        >
          <Menu className="size-5" />
        </SheetTrigger>
        <SheetContent side="left" className="w-[280px] p-0 border-r-0" showCloseButton={false}>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          {sidebarContent}
        </SheetContent>
      </Sheet>

      <div className="flex flex-1 flex-col overflow-hidden">
        <ChatArea
          session={activeSession}
          isLoading={isLoading}
          onSend={sendMessage}
          onTogglePublic={togglePublic}
        />
      </div>
    </div>
  )
}
