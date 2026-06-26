/**
 * 사이드패널 로그인 게이트 — Phase 3 네이티브 OAuth 진입 UI.
 */
import type { ReactNode } from 'react'
import { useExtensionAuthContext } from '@/features/auth/context/ExtensionAuthProvider'

interface AuthGateProps {
  children: ReactNode
}

export function AuthGate({ children }: AuthGateProps) {
  const {
    isAuthenticated,
    isLoading,
    isLoggingIn,
    error,
    loginWithGoogle,
    loginWithDev,
  } = useExtensionAuthContext()

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-xs text-slate-400">
        세션 확인 중…
      </div>
    )
  }

  if (isAuthenticated) {
    return <div className="flex min-h-0 flex-1 flex-col">{children}</div>
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-10 text-center">
      <div className="text-3xl">🔐</div>
      <div>
        <p className="text-sm font-semibold text-slate-800">Synapse 로그인</p>
        <p className="mt-1 max-w-[220px] text-xs leading-relaxed text-slate-500">
          Google 계정으로 로그인하면 AI 채팅과 아카이브 기능을 사용할 수 있습니다.
        </p>
      </div>

      <button
        type="button"
        onClick={() => void loginWithGoogle()}
        disabled={isLoggingIn}
        className="w-full max-w-[240px] rounded-full border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-800 shadow-sm transition-colors hover:bg-slate-50 disabled:opacity-60"
      >
        {isLoggingIn ? 'Google 로그인 중…' : 'Google로 로그인'}
      </button>

      {import.meta.env.DEV ? (
        <button
          type="button"
          onClick={() => void loginWithDev()}
          disabled={isLoggingIn}
          className="text-[11px] text-slate-400 underline-offset-2 hover:text-slate-600 hover:underline disabled:opacity-60"
        >
          Dev 로그인 (로컬)
        </button>
      ) : null}

      {error ? <p className="max-w-[240px] text-[11px] text-rose-500">{error}</p> : null}
    </div>
  )
}
