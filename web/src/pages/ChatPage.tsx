import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
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

  // Sync URL → activeSession
  useEffect(() => {
    if (sessionId && sessionId !== activeSession?.id) {
      setActiveSession(sessionId)
    }
  }, [sessionId, activeSession?.id, setActiveSession])

  // Auto-select first session when landing on /
  useEffect(() => {
    if (!sessionId && sessions.length > 0 && !activeSession) {
      navigate(`/session/${sessions[0].id}`, { replace: true })
    }
  }, [sessionId, sessions, activeSession, navigate])

  function handleSelectSession(id: string) {
    navigate(`/session/${id}`)
    setMobileOpen(false)
  }

  function handleNewSession() {
    createSession().then(() => {
      // After creation, the newest session is first in the list
      // useChat will set it as active, then we sync URL
    })
    setMobileOpen(false)
  }

  function handleDeleteSession(id: string) {
    deleteSession(id)
    if (activeSession?.id === id) {
      navigate('/', { replace: true })
    }
  }

  // Sync activeSession → URL (for createSession)
  useEffect(() => {
    if (activeSession && activeSession.id !== sessionId) {
      navigate(`/session/${activeSession.id}`, { replace: true })
    }
  }, [activeSession, sessionId, navigate])

  const sidebarContent = (
    <Sidebar
      sessions={sessions}
      activeSessionId={activeSession?.id ?? null}
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
        <SheetContent side="left" className="w-[280px] p-0">
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
