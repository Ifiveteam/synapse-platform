import { createContext, useContext, type ReactNode } from 'react'
import { useChat } from '@/features/chat/hooks/useChat'

type ChatContextValue = ReturnType<typeof useChat>

const ChatContext = createContext<ChatContextValue | null>(null)

/** ChatView·ChatInput이 동일한 메시지 스트림을 공유하도록 세션을 한 번만 구독한다. */
export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChat()

  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>
}

export function useChatContext() {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChatContext는 ChatProvider 내부에서만 사용할 수 있습니다.')
  }
  return context
}
