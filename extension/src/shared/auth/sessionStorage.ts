import { STORAGE_KEYS } from '@/shared/constants/storageKeys'

import type { AuthSessionSnapshot, AuthUserSnapshot } from './types'

export async function readAuthSession(): Promise<AuthSessionSnapshot | null> {
  if (!chrome.storage?.local) return null

  const result = await chrome.storage.local.get([
    STORAGE_KEYS.ACCESS_TOKEN,
    STORAGE_KEYS.REFRESH_TOKEN,
    STORAGE_KEYS.AUTH_USER,
  ])

  const accessToken = result[STORAGE_KEYS.ACCESS_TOKEN]
  const refreshToken = result[STORAGE_KEYS.REFRESH_TOKEN]
  const user = result[STORAGE_KEYS.AUTH_USER] as AuthUserSnapshot | undefined

  if (
    typeof accessToken !== 'string' ||
    accessToken.length === 0 ||
    typeof refreshToken !== 'string' ||
    refreshToken.length === 0 ||
    !user?.id
  ) {
    return null
  }

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    user,
  }
}

export async function storeAuthSession(session: AuthSessionSnapshot): Promise<void> {
  if (!chrome.storage?.local) return

  await chrome.storage.local.set({
    [STORAGE_KEYS.ACCESS_TOKEN]: session.access_token,
    [STORAGE_KEYS.REFRESH_TOKEN]: session.refresh_token,
    [STORAGE_KEYS.AUTH_USER]: session.user,
  })
}

export async function clearAuthSession(): Promise<void> {
  if (!chrome.storage?.local) return

  await chrome.storage.local.remove([
    STORAGE_KEYS.ACCESS_TOKEN,
    STORAGE_KEYS.REFRESH_TOKEN,
    STORAGE_KEYS.AUTH_USER,
  ])
}
