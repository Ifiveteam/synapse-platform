/**
 * Synapse 웹(프론트) ↔ 익스텐션 인증 브릿지.
 * 웹이 1회용 code만 전달하고, 익스텐션이 백엔드와 직접 토큰 교환한다.
 */
import { exchangeExtensionCode } from '@/shared/api/extensionAuth'
import { terminateAuthSession } from '@/shared/auth/sessionLifecycle'
import { storeAuthSession } from '@/shared/auth/sessionStorage'
import {
  SYNAPSE_WEB_MESSAGE_SOURCE,
  type SynapseWebAuthMessage,
} from '@/shared/auth/types'

/** manifest·vite와 맞춘 Synapse 웹 dev/prod origin 허용 목록 */
const ALLOWED_FRONTEND_ORIGINS = new Set([
  'http://localhost:5173',
  'http://localhost:5174',
  'http://localhost:3000',
])

function isSynapseWebAuthMessage(data: unknown): data is SynapseWebAuthMessage {
  if (!data || typeof data !== 'object') return false
  const message = data as Record<string, unknown>
  if (message.source !== SYNAPSE_WEB_MESSAGE_SOURCE) return false

  if (message.type === 'AUTH_CLEAR') return true

  if (message.type !== 'AUTH_CODE') return false

  const payload = message.payload as Record<string, unknown> | undefined
  return typeof payload?.code === 'string' && payload.code.length > 0
}

async function handleAuthCode(code: string) {
  const session = await exchangeExtensionCode(code)
  await storeAuthSession(session)
}

export function initAuthBridge() {
  window.addEventListener('message', (event) => {
    if (event.source !== window) return
    if (!ALLOWED_FRONTEND_ORIGINS.has(event.origin)) return
    if (!isSynapseWebAuthMessage(event.data)) return

    if (event.data.type === 'AUTH_CLEAR') {
      void terminateAuthSession()
      return
    }

    void handleAuthCode(event.data.payload.code).catch((error) => {
      console.error('[Synapse AuthBridge] code 교환 실패:', error)
    })
  })
}
