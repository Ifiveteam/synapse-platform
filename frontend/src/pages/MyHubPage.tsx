import { IdealManagementPage } from "@/pages/IdealManagementPage";
import { MyAnalysesPage } from "@/pages/MyAnalysesPage";

/**
 * /me 통합 허브.
 * 개인성향 분석 목록 / 이상향 관리 두 섹션만 노출한다.
 * 각 섹션은 실제 페이지 컴포넌트를 embedded 모드로 재사용한다.
 */
export function MyHubPage() {
  return (
    <div className="flex min-h-full w-full flex-col gap-6 px-4 py-5 sm:px-6 sm:py-6 lg:w-1/2">
      <section className="border-border bg-muted/20 rounded-2xl border p-5">
        <MyAnalysesPage embedded latestOnly />
      </section>
      <section className="border-border bg-muted/20 rounded-2xl border p-5">
        <IdealManagementPage embedded activeOnly />
      </section>
    </div>
  );
}
