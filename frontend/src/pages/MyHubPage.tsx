import { AccountSidePanel } from "@/components/shell/AccountSidePanel";
import { IdealManagementPage } from "@/pages/IdealManagementPage";
import { MyAnalysesPage } from "@/pages/MyAnalysesPage";

/**
 * /me 통합 허브.
 * 좌측: 계정정보 + 현재 적용 이상향 / 우상단: 개인성향 분석 목록 / 우하단: 이상향 관리.
 * 우측 두 섹션은 각각 실제 페이지 컴포넌트를 embedded 모드로 재사용한다.
 */
export function MyHubPage() {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-6xl flex-col gap-6 px-6 py-8 lg:flex-row">
      <aside className="w-full shrink-0 lg:w-72">
        <AccountSidePanel />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-6">
        <section className="border-border bg-muted/20 rounded-2xl border p-5 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto">
          <MyAnalysesPage embedded />
        </section>
        <section className="border-border bg-muted/20 rounded-2xl border p-5 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto">
          <IdealManagementPage embedded />
        </section>
      </div>
    </div>
  );
}
