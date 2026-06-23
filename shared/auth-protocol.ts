/** Synapse 웹 ↔ 익스텐션 content script postMessage 프로토콜 SSOT */

export const SYNAPSE_WEB_MESSAGE_SOURCE = 'synapse-web' as const

export type SynapseWebAuthMessage =
  | {
      source: typeof SYNAPSE_WEB_MESSAGE_SOURCE
      type: 'AUTH_CODE'
      payload: { code: string }
    }
  | {
      source: typeof SYNAPSE_WEB_MESSAGE_SOURCE
      type: 'AUTH_CLEAR'
    }
