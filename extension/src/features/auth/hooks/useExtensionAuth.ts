import { useCallback, useEffect, useState } from 'react'

import {
  loginWithDevSession,
  loginWithGoogleOAuth,
  logoutExtensionSession,
} from '@/features/auth/services/extensionOAuth'
import { readAuthSession } from '@/shared/auth/sessionStorage'
import type { AuthSessionSnapshot, AuthUserSnapshot } from '@/shared/auth/types'
import { STORAGE_KEYS } from '@/shared/constants/storageKeys'

interface ExtensionAuthState {
  session: AuthSessionSnapshot | null
  user: AuthUserSnapshot | null
  isAuthenticated: boolean
  isLoading: boolean
  isLoggingIn: boolean
  error: string | null
  loginWithGoogle: () => Promise<void>
  loginWithDev: () => Promise<void>
  logout: () => Promise<void>
}

export function useExtensionAuth(): ExtensionAuthState {
  const [session, setSession] = useState<AuthSessionSnapshot | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const syncFromStorage = useCallback(async () => {
    const stored = await readAuthSession()
    setSession(stored)
  }, [])

  useEffect(() => {
    void syncFromStorage().finally(() => setIsLoading(false))

    const handleStorageChange = (
      changes: Record<string, chrome.storage.StorageChange>,
      areaName: string,
    ) => {
      if (areaName !== 'local') return
      const authKeys = new Set<string>([
        STORAGE_KEYS.ACCESS_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.AUTH_USER,
      ])
      if (!Object.keys(changes).some((key) => authKeys.has(key))) return
      void syncFromStorage()
    }

    chrome.storage.onChanged.addListener(handleStorageChange)
    return () => chrome.storage.onChanged.removeListener(handleStorageChange)
  }, [syncFromStorage])

  const loginWithGoogle = useCallback(async () => {
    setIsLoggingIn(true)
    setError(null)
    try {
      const next = await loginWithGoogleOAuth()
      setSession(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google 로그인에 실패했습니다')
    } finally {
      setIsLoggingIn(false)
    }
  }, [])

  const loginWithDev = useCallback(async () => {
    setIsLoggingIn(true)
    setError(null)
    try {
      const next = await loginWithDevSession()
      setSession(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dev 로그인에 실패했습니다')
    } finally {
      setIsLoggingIn(false)
    }
  }, [])

  const logout = useCallback(async () => {
    setError(null)
    await logoutExtensionSession()
    setSession(null)
  }, [])

  return {
    session,
    user: session?.user ?? null,
    isAuthenticated: Boolean(session),
    isLoading,
    isLoggingIn,
    error,
    loginWithGoogle,
    loginWithDev,
    logout,
  }
}
