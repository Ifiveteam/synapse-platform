import { revokeExtensionSession } from '@/features/auth/services/extensionAuth'
import { clearAuthSession, readAuthSession } from '@/shared/auth/sessionStorage'

/** refresh token revoke(실패 무시) 후 로컬 세션을 제거한다. */
export async function terminateAuthSession(): Promise<void> {
  const session = await readAuthSession()
  if (session?.refresh_token) {
    await revokeExtensionSession(session.refresh_token).catch(() => {
      // revoke 실패해도 로컬 세션은 제거
    })
  }
  await clearAuthSession()
}
