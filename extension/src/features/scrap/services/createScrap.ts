/**
 * Scrap 생성 오케스트레이터 — FAB·채팅 등 진입 경로를 단일 API로 수렴한다.
 * 모든 스크랩은 현재 탭 페이지 본문(raw_body) 기준으로 저장한다.
 */
import { queryActiveTabContextForSend } from '@/features/archiver/services/queryTabContext'
import { submitScrapCreateViaBackground } from '@/features/scrap/services/scrapBackgroundBridge'
import type { ScrapResponse } from '@/features/scrap/models/types'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

const RAW_BODY_MAX_CHARS = 5000

export const SCRAP_CREATED_MESSAGE = 'SCRAP_CREATED' as const

export type CreateScrapOptions = {
  customCategory?: string | null
}

function truncateRawBody(body: string): string {
  const normalized = body.trim()
  if (normalized.length <= RAW_BODY_MAX_CHARS) {
    return normalized
  }
  return normalized.slice(0, RAW_BODY_MAX_CHARS)
}

function notifyScrapCreated(): void {
  if (!isExtensionContextValid()) return

  chrome.runtime.sendMessage({ action: SCRAP_CREATED_MESSAGE }).catch(() => {
    // 사이드패널 미오픈 등 수신자 없음 — 무시
  })
}

/** FAB·채팅·아카이버 시그널 등에서 호출하는 공용 페이지 스크랩 진입점 */
export async function createScrap(options?: CreateScrapOptions): Promise<ScrapResponse> {
  const context = await queryActiveTabContextForSend()
  if (!context) {
    throw new Error('활성 탭 맥락을 가져올 수 없습니다.')
  }

  const rawBody = truncateRawBody(context.body ?? '')
  if (!rawBody) {
    throw new Error('페이지 본문을 추출하지 못했습니다.')
  }

  const customCategory = options?.customCategory?.trim() || null

  const scrap = await submitScrapCreateViaBackground({
    url: context.url,
    title: context.title,
    raw_body: rawBody,
    ...(customCategory ? { custom_category: customCategory } : {}),
  })

  notifyScrapCreated()
  return scrap
}
