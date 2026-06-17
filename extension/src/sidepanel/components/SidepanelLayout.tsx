/**
 * 사이드패널 3단 Flex 프레임 — 헤더·푸터 고정, main만 독립 스크롤.
 */
import { useState } from 'react'
import { ChatInput } from '@/features/chat/components/ChatInput'
import { ChatView } from '@/features/chat/components/ChatView'
import { ChatProvider } from '@/features/chat/context/ChatProvider'
import { ScrapView } from '@/features/scrap/components/ScrapView'
import { SidepanelHeader, type SidepanelTab } from './SidepanelHeader'

export function SidepanelLayout() {
  const [activeTab, setActiveTab] = useState<SidepanelTab>('chat')

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-slate-50 font-sans text-slate-900 antialiased">
      <SidepanelHeader activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'chat' ? (
        <ChatProvider>
          <main className="min-h-0 flex-1 w-full overflow-y-auto px-4 py-4">
            <ChatView />
          </main>

          <footer className="w-full shrink-0 border-t border-slate-100 bg-white p-3 shadow-[0_-2px_10px_rgba(0,0,0,0.02)]">
            <ChatInput />
          </footer>
        </ChatProvider>
      ) : (
        <main className="min-h-0 flex-1 w-full overflow-y-auto px-4 py-4">
          <ScrapView />
        </main>
      )}
    </div>
  )
}
