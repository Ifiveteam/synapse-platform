import { IdealManagementPage } from "@/pages/IdealManagementPage";
import { MyAnalysesPage } from "@/pages/MyAnalysesPage";

/**
 * /me 통합 허브.
 * 개인성향 분석 목록 / 이상향 관리 두 목록을 좌우로 나란히 배치.
 * 각 목록은 최신순 전체 + 페이지네이션(칸을 넘어가면 페이지로 관리).
 * 목록 안의 항목을 누르면 해당 상세 화면으로 바로 이동한다.
 */
export function MyHubPage() {
  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-6 p-4 sm:p-6 lg:flex-row">
      <section className="border-border bg-muted/20 flex min-h-[200px] min-w-0 flex-1 flex-col overflow-y-auto rounded-2xl border p-5">
        <MyAnalysesPage />
      </section>
      <section className="border-border bg-muted/20 flex min-h-[200px] min-w-0 flex-1 flex-col overflow-y-auto rounded-2xl border p-5">
        <IdealManagementPage />
      </section>
    </div>
  );
}
