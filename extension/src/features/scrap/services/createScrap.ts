/**
 * Scrap 생성 오케스트레이터 — FAB·채팅 등 진입 경로를 단일 API로 수렴한다.
 */
import { queryActiveTabContextForSend } from '@/features/archiver/services/queryTabContext'
import type { ScrapResponse } from '@/features/scrap/models/types'
import { createScrap as postScrap } from '@/features/scrap/services/scrapClient'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

const RAW_BODY_MAX_CHARS = 5000

export const SCRAP_CREATED_MESSAGE = 'SCRAP_CREATED' as const

export type CreateWebScrapOptions = {
  source_type: 'web'
}

export type CreateChatScrapOptions = {
  source_type: 'chat'
  session_id: string
  url?: string | null
  title?: string | null
}

export type CreateScrapOptions = CreateWebScrapOptions | CreateChatScrapOptions

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

async function createWebScrap(): Promise<ScrapResponse> {
  const context = await queryActiveTabContextForSend()
  if (!context) {
    throw new Error('활성 탭 맥락을 가져올 수 없습니다.')
  }

  const rawBody = truncateRawBody(context.body ?? '')
  if (!rawBody) {
    throw new Error('페이지 본문을 추출하지 못했습니다.')
  }

  return postScrap({
    source_type: 'web',
    url: context.url,
    title: context.title,
    raw_body: rawBody,
  })
}

async function createChatScrap(options: CreateChatScrapOptions): Promise<ScrapResponse> {
  const sessionId = options.session_id.trim()
  if (!sessionId) {
    throw new Error('chat 스크랩에는 session_id가 필요합니다.')
  }

  return postScrap({
    source_type: 'chat',
    session_id: sessionId,
    url: options.url ?? null,
    title: options.title ?? null,
  })
}

/** FAB 또는 채팅 액션에서 호출하는 공용 스크랩 생성 진입점 */
export async function createScrap(options: CreateScrapOptions): Promise<ScrapResponse> {
  const scrap =
    options.source_type === 'web'
      ? await createWebScrap()
      : await createChatScrap(options)

  notifyScrapCreated()
  return scrap
}
