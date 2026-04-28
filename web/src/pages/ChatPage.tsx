import { useState } from 'react'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Sidebar } from '@/components/chat/Sidebar'
import { ChatArea } from '@/components/chat/ChatArea'
import { useChat } from '@/hooks/useChat'

export function ChatPage() {
  const { sessions, activeSession, isLoading, setActiveSession, createSession, deleteSession, renameSession, sendMessage } = useChat()
  const [mobileOpen, setMobileOpen] = useState(false)

  const sidebarContent = (
    <Sidebar
      sessions={sessions}
      activeSessionId={activeSession?.id ?? null}
      onSelectSession={(id) => {
        setActiveSession(id)
        setMobileOpen(false)
      }}
      onNewSession={() => {
        createSession()
        setMobileOpen(false)
      }}
      onDeleteSession={deleteSession}
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
        />
      </div>
    </div>
  )
}
