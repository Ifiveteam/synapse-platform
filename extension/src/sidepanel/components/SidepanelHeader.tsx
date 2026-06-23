/**
 * 사이드패널 상단 바 — FAB가 가려져도 트래킹·탭 전환·로그인 상태를 유지한다.
 */
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { useExtensionAuthContext } from '@/features/auth/context/ExtensionAuthProvider'
import { useTracking } from '@/features/tracking/hooks/useTracking'

export type SidepanelTab = 'chat' | 'scrap'

interface SidepanelHeaderProps {
  activeTab: SidepanelTab
  onTabChange: (tab: SidepanelTab) => void
}

export function SidepanelHeader({ activeTab, onTabChange }: SidepanelHeaderProps) {
  const { isTracking, setTracking } = useTracking()
  const { isAuthenticated, user, logout } = useExtensionAuthContext()

  return (
    <header className="flex w-full shrink-0 flex-col gap-2 border-b border-slate-100 bg-white px-4 py-2.5 shadow-sm">
      <div className="flex w-full items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-lg font-black tracking-wider text-slate-900">SYNAPSE</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
            v1.0
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {isAuthenticated && user ? (
            <div className="flex max-w-[140px] items-center gap-1.5">
              <span
                className="truncate text-[10px] font-medium text-slate-600"
                title={user.email}
              >
                {user.name || user.email}
              </span>
              <button
                type="button"
                onClick={() => void logout()}
                className="shrink-0 text-[10px] text-slate-400 underline-offset-2 hover:text-slate-700 hover:underline"
              >
                로그아웃
              </button>
            </div>
          ) : null}

          <Label htmlFor="tracking-mode" className="text-xs font-medium text-slate-500">
            {isTracking ? '라이브 추적 중' : '추적 중단'}
          </Label>
          <Switch
            id="tracking-mode"
            checked={isTracking}
            onCheckedChange={setTracking}
            aria-label="전역 트래킹 스위치"
          />
        </div>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(value) => onTabChange(value as SidepanelTab)}
        className="w-full"
      >
        <TabsList className="grid h-8 w-full grid-cols-2 rounded-md bg-slate-100/80 p-0.5">
          <TabsTrigger
            value="chat"
            className="rounded-sm py-1 text-xs font-semibold data-active:bg-white data-active:text-slate-950 data-active:shadow-sm"
          >
            💬 AI 인텔리전스
          </TabsTrigger>
          <TabsTrigger
            value="scrap"
            className="rounded-sm py-1 text-xs font-semibold data-active:bg-white data-active:text-slate-950 data-active:shadow-sm"
          >
            📌 컨텍스트 보관함
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </header>
  )
}
