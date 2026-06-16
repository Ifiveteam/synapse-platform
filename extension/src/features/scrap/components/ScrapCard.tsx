/**
 * Synapse 개별 스크랩 카드 컴포넌트
 * 개별 지식 스크랩 아이템을 Shadcn Card 형태로 표현하며,
 * 원본 이동 링크 및 버블링이 차단된 삭제 이벤트를 처리합니다.
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'
import type { ScrapItem } from '../hooks/useScrap'

interface ScrapCardProps {
  item: ScrapItem
  onDelete: (id: string) => void
}

function resolveHostname(url: string) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export function ScrapCard({ item, onDelete }: ScrapCardProps) {
  /** 익스텐션 컨텍스트는 chrome.tabs 우선, 그 외 환경은 window.open 폴백 */
  const handleCardClick = () => {
    if (isExtensionContextValid() && chrome.tabs) {
      chrome.tabs.create({ url: item.url })
      return
    }
    window.open(item.url, '_blank', 'noopener,noreferrer')
  }

  return (
    <Card
      className="group relative cursor-pointer overflow-hidden border-slate-100 bg-white shadow-sm transition-all duration-200 hover:border-slate-200 hover:shadow-md"
      onClick={handleCardClick}
    >
      <div className="absolute top-0 left-0 h-full w-1 bg-slate-900 transition-colors group-hover:bg-slate-700" />

      <CardHeader className="flex flex-row items-start justify-between space-y-0 p-3 pr-10 pb-1 pl-4">
        <CardTitle
          className="line-clamp-2 text-xs leading-snug font-bold tracking-tight break-all text-slate-800 group-hover:text-slate-950"
          title={item.title}
        >
          {item.title}
        </CardTitle>
      </CardHeader>

      <CardContent className="flex items-center justify-between p-3 pt-0 pl-4">
        <span className="max-w-[160px] truncate text-[10px] font-medium text-slate-400">
          {resolveHostname(item.url)}
        </span>
        <span className="shrink-0 text-[9px] text-slate-400">{item.scrapedAt}</span>
      </CardContent>

      <Button
        type="button"
        size="icon-xs"
        variant="ghost"
        className="absolute top-1.5 right-1.5 z-10 text-slate-400 opacity-0 transition-all duration-150 group-hover:opacity-100 hover:bg-rose-50 hover:text-rose-600"
        onClick={(e) => {
          e.stopPropagation()
          onDelete(item.id)
        }}
        aria-label="스크랩 삭제"
      >
        <svg
          className="h-3.5 w-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
          />
        </svg>
      </Button>
    </Card>
  )
}
