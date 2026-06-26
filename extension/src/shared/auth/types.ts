/** 프론트·익스텐션이 공유하는 로그인 유저 스냅샷 */
export interface AuthUserSnapshot {
  id: string
  email: string
  name: string
  picture: string | null
}

/** 익스텐션 chrome.storage 세션 — access + extension refresh */
export interface AuthSessionSnapshot {
  access_token: string
  refresh_token: string
  user: AuthUserSnapshot
}

export {
  SYNAPSE_WEB_MESSAGE_SOURCE,
  type SynapseWebAuthMessage,
} from '@/shared/auth/protocol'
