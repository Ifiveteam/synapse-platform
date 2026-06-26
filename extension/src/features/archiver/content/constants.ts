/**
 * 페이지 추출 공통 상수.
 *
 * 역할: 여러 extract 모듈이 공유하는 DOM 셀렉터·태그 목록 SSOT.
 * 하는 일:
 * - Synapse 익스텐션 host root id (본문 수집에서 제외)
 * - 블록 후보 태그 (DIV, MAIN, ARTICLE 등)
 * - 노이즈 태그·셀렉터 (script, style, svg 등 제거 대상)
 */
import { SYNAPSE_EXTENSION_ROOT_ID } from '@/shared/constants/extensionDom'

export const SYNAPSE_HOST_ROOT_ID = SYNAPSE_EXTENSION_ROOT_ID

export const BLOCK_TAGS = new Set(['DIV', 'SECTION', 'ASIDE', 'ARTICLE', 'MAIN'])

export const NOISE_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'CANVAS'])

export const NOISE_SELECTORS = [
  'script',
  'style',
  'noscript',
  'svg',
  'canvas',
  'iframe',
  'link[rel="stylesheet"]',
]
