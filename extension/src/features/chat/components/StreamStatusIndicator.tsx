/** 스트리밍 진행 상태 — status / need_dom 전용 인디케이터 */

import type {
  ArchiverStreamStatus,
  ArchiverStructuredStatus,
} from '@/features/archiver/models/types'

interface StreamStatusIndicatorProps {
  status: ArchiverStreamStatus
}

const ENGINE_LABELS: Record<string, string> = {
  collect_node: '페이지',
  rag_node: '기억',
  search_node: '검색',
}

function isStructuredStatus(status: ArchiverStreamStatus): status is ArchiverStructuredStatus {
  return typeof status === 'object' && status !== null && 'message' in status
}

function displayMessage(status: ArchiverStreamStatus): string {
  if (isStructuredStatus(status)) {
    return status.message.trim()
  }
  return status.trim()
}

export function StreamStatusIndicator({ status }: StreamStatusIndicatorProps) {
  const text = displayMessage(status)
  if (!text) return null

  const engines = isStructuredStatus(status) ? status.engines : undefined
  const showChips = Boolean(engines && engines.length > 0)

  return (
    <div
      className="flex flex-col gap-1.5 rounded-xl border border-indigo-100/80 bg-gradient-to-r from-indigo-50/90 to-slate-50/90 px-3 py-2 shadow-sm"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-2.5">
        <span
          className="mt-0.5 size-3.5 shrink-0 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-500"
          aria-hidden
        />
        <p className="text-[11px] leading-relaxed text-slate-600">{text}</p>
      </div>
      {showChips && (
        <div className="flex flex-wrap gap-1 pl-6">
          {engines!.map((engine) => (
            <span
              key={engine}
              className="rounded-full border border-indigo-200/80 bg-white/80 px-2 py-0.5 text-[10px] font-medium text-indigo-700"
            >
              {ENGINE_LABELS[engine] ?? engine}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
