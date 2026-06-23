import { API_BASE } from '@/shared/api/config'
import { exchangeExtensionCode } from '@/shared/api/extensionAuth'
import { terminateAuthSession } from '@/shared/auth/sessionLifecycle'
import { storeAuthSession } from '@/shared/auth/sessionStorage'
import type { AuthSessionSnapshot } from '@/shared/auth/types'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

function getIdentityRedirectUrl(): string {
  if (!chrome.identity?.getRedirectURL) {
    throw new Error('chrome.identity API를 사용할 수 없습니다')
  }
  return chrome.identity.getRedirectURL()
}

function launchWebAuthFlow(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow({ url, interactive: true }, (responseUrl) => {
      const error = chrome.runtime.lastError
      if (error || !responseUrl) {
        reject(new Error(error?.message ?? 'OAuth가 취소되었습니다'))
        return
      }
      resolve(responseUrl)
    })
  })
}

/** Phase 3 — 익스텐션 네이티브 Google OAuth */
export async function loginWithGoogleOAuth(): Promise<AuthSessionSnapshot> {
  if (!isExtensionContextValid()) {
    throw new Error('익스텐션 컨텍스트가 유효하지 않습니다')
  }

  const redirectUri = getIdentityRedirectUrl()
  const loginUrl = `${API_BASE}/api/v1/auth/extension/login?redirect_uri=${encodeURIComponent(redirectUri)}`
  const responseUrl = await launchWebAuthFlow(loginUrl)

  const linkCode = new URL(responseUrl).searchParams.get('code')
  if (!linkCode) {
    throw new Error('OAuth 콜백에 연동 code가 없습니다')
  }

  const session = await exchangeExtensionCode(linkCode)
  await storeAuthSession(session)
  return session
}

/** DEV — extension-dev-login (Google 없이) */
export async function loginWithDevSession(): Promise<AuthSessionSnapshot> {
  const response = await fetch(`${API_BASE}/api/v1/auth/extension-dev-login`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error(`extension-dev-login failed: ${response.status}`)
  }

  const session = (await response.json()) as AuthSessionSnapshot
  if (!session.access_token || !session.refresh_token || !session.user?.id) {
    throw new Error('dev-login 응답이 올바르지 않습니다')
  }

  await storeAuthSession(session)
  return session
}

export async function logoutExtensionSession(): Promise<void> {
  await terminateAuthSession()
}
