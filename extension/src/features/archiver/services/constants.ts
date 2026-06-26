/**
 * TabContext 서비스 공통 상수.
 *
 * 역할: tabQuery·domCache·frameCollect가 공유하는 고정값 SSOT.
 * 하는 일:
 * - content script 추출 메시지 타입
 * - DOM 캐시 URL 정규화 시 제거할 트래킹 쿼리 키
 * - map 페이지 감지 URL 패턴
 */
import { SYNAPSE_EXTRACT_PAGE_TEXT } from '@/features/archiver/utils/pageContextProtocol'

export const EXTRACT_MESSAGE = { type: SYNAPSE_EXTRACT_PAGE_TEXT } as const

export const TRACKING_QUERY_KEYS = new Set([
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'fbclid',
  'gclid',
  'mc_cid',
  'mc_eid',
  'ref',
  'source',
  'spm',
  'igshid',
])

export const MAP_URL_PATTERNS = [
  'naver.com/map',
  'map.naver.com',
  'google.com/maps',
  'maps.google.com',
] as const
