/**
 * Synapse 개별 스크랩 카드 컴포넌트
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { ScrapListItem } from '@/features/scrap/models/types'
import { isExtensionContextValid } from '@/shared/utils/extensionContext'

interface ScrapCardProps {
  item: ScrapListItem
  onDelete: (id: string) => void
}

function resolveHostname(url: string | null) {
  if (!url) return 'URL 없음'
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function formatCreatedAt(iso: string) {
  const value = new Date(iso)
  if (Number.isNaN(value.getTime())) return iso
  return value.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function ScrapCard({ item, onDelete }: ScrapCardProps) {
  const displayTitle = item.title?.trim() || item.summary
  const hasUrl = Boolean(item.url?.trim())

  const handleCardClick = () => {
    if (!hasUrl) return

    if (isExtensionContextValid() && chrome.tabs) {
      chrome.tabs.create({ url: item.url! })
      return
    }
    window.open(item.url!, '_blank', 'noopener,noreferrer')
  }

  return (
    <Card
      className={`group relative overflow-hidden border-slate-100 bg-white shadow-sm transition-all duration-200 hover:border-slate-200 hover:shadow-md ${
        hasUrl ? 'cursor-pointer' : 'cursor-default'
      }`}
      onClick={handleCardClick}
    >
      <div className="absolute top-0 left-0 h-full w-1 bg-slate-900 transition-colors group-hover:bg-slate-700" />

      <CardHeader className="flex flex-row items-start justify-between space-y-0 p-3 pr-10 pb-1 pl-4">
        <CardTitle
          className="line-clamp-2 text-xs leading-snug font-bold tracking-tight break-all text-slate-800 group-hover:text-slate-950"
          title={displayTitle}
        >
          {displayTitle}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-2 p-3 pt-0 pl-4">
        <p className="line-clamp-2 text-[10px] leading-relaxed text-slate-500">{item.summary}</p>
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 flex-col gap-0.5">
            <span className="truncate text-[10px] font-medium text-slate-400">
              {item.category}
            </span>
            <span className="max-w-[160px] truncate text-[10px] text-slate-400">
              {resolveHostname(item.url)}
            </span>
          </div>
          <span className="shrink-0 text-[9px] text-slate-400">
            {formatCreatedAt(item.createdAt)}
          </span>
        </div>
        {item.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {item.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] text-slate-500"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
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
