/**
 * 사이드패널 인증 컨텍스트 — 헤더·채팅 게이트가 동일 세션 상태를 공유한다.
 */
import { createContext, useContext, type ReactNode } from 'react'
import { useExtensionAuth } from '@/features/auth/hooks/useExtensionAuth'

type ExtensionAuthContextValue = ReturnType<typeof useExtensionAuth>

const ExtensionAuthContext = createContext<ExtensionAuthContextValue | null>(null)

export function ExtensionAuthProvider({ children }: { children: ReactNode }) {
  const value = useExtensionAuth()
  return (
    <ExtensionAuthContext.Provider value={value}>{children}</ExtensionAuthContext.Provider>
  )
}

export function useExtensionAuthContext(): ExtensionAuthContextValue {
  const ctx = useContext(ExtensionAuthContext)
  if (!ctx) {
    throw new Error('useExtensionAuthContext must be used within ExtensionAuthProvider')
  }
  return ctx
}
