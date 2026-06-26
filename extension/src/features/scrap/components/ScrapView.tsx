/**
 * Synapse 컨텍스트 보관함 메인 뷰 컴포넌트
 */
import { useScrap } from '../hooks/useScrap'
import { ScrapCard } from './ScrapCard'

export function ScrapView() {
  const { scrapList, isLoading, error, deleteScrap } = useScrap()

  const sortedScrapList = [...scrapList].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  )

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-xs text-slate-400">
        보관함 데이터를 동기화 중입니다...
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-xs font-semibold text-rose-500">보관함을 불러오지 못했습니다</p>
        <p className="mt-1 max-w-[220px] text-[10px] leading-relaxed text-slate-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-full flex-col gap-3">
      {sortedScrapList.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400/80">
          <div className="mb-3 text-3xl">📌</div>
          <p className="text-xs font-semibold text-slate-600">보관함이 비어있습니다</p>
          <p className="mt-1 max-w-[200px] text-[10px] leading-relaxed text-slate-400">
            웹서핑 중 저장하고 싶은 핵심 페이지를 발견하면 FAB 위젯의 📌 버튼을 눌러보세요!
          </p>
        </div>
      ) : (
        sortedScrapList.map((item) => (
          <ScrapCard key={item.id} item={item} onDelete={(id) => void deleteScrap(id)} />
        ))
      )}
    </div>
  )
}
