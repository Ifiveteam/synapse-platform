import { X } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ChatMessages } from "@/components/home/chat-messages";
import { CuratorInput } from "@/components/home/curator-input";
import { IdealManagementPage } from "@/pages/IdealManagementPage";
import { MyAnalysesPage } from "@/pages/MyAnalysesPage";
import { ROUTES } from "@/routes";
import { useChatStore } from "@/stores/chat";

/** 우측 채팅 패널 — 홈과 같은 큐레이터 세션을 공유한다. */
function HubChatPanel() {
  const hasMessages = useChatStore((s) => s.messages.length > 0);
  const clearMessages = useChatStore((s) => s.clearMessages);

  return (
    <div className="border-border bg-card flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border">
      <div className="border-border flex shrink-0 items-center justify-between border-b px-5 py-3">
        <h2 className="text-sm font-semibold tracking-tight">큐레이터</h2>
        {hasMessages && (
          <button
            type="button"
            onClick={clearMessages}
            title="채팅 비우기"
            className="text-muted-foreground hover:text-foreground hover:bg-secondary flex h-7 w-7 items-center justify-center rounded-full transition-colors"
          >
            <X size={15} />
          </button>
        )}
      </div>

      {hasMessages ? (
        <ChatMessages />
      ) : (
        <div className="text-muted-foreground flex min-h-0 flex-1 items-center justify-center px-6 text-center text-sm">
          큐레이터에게 무엇이든 물어보세요.
        </div>
      )}

      <CuratorInput />
    </div>
  );
}

/**
 * /me 통합 허브.
 * 좌측: 개인성향 분석 목록 / 이상향 관리 두 섹션을 상하 반반.
 * 우측: 큐레이터 채팅창.
 * 각 박스 어디를 눌러도 해당 전체 페이지로 이동한다
 * (내부 액션 버튼은 stopPropagation으로 예외 처리).
 */
export function MyHubPage() {
  const navigate = useNavigate();
  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-6 p-4 sm:p-6 lg:flex-row">
      {/* 좌: 두 박스 상하 반반 */}
      <div className="flex min-h-0 flex-1 flex-col gap-6">
        <section
          role="link"
          tabIndex={0}
          onClick={() => navigate(ROUTES.myAnalyses)}
          onKeyDown={(e) => {
            if (e.key === "Enter") navigate(ROUTES.myAnalyses);
          }}
          className="border-border bg-muted/20 hover:border-primary/40 min-h-[200px] flex-1 cursor-pointer overflow-y-auto rounded-2xl border p-5 transition-colors"
        >
          <MyAnalysesPage embedded latestOnly />
        </section>
        <section
          role="link"
          tabIndex={0}
          onClick={() => navigate(ROUTES.idealManagement)}
          onKeyDown={(e) => {
            if (e.key === "Enter") navigate(ROUTES.idealManagement);
          }}
          className="border-border bg-muted/20 hover:border-primary/40 min-h-[200px] flex-1 cursor-pointer overflow-y-auto rounded-2xl border p-5 transition-colors"
        >
          <IdealManagementPage embedded activeOnly />
        </section>
      </div>

      {/* 우: 채팅창 */}
      <div className="flex min-h-[320px] min-w-0 flex-1 flex-col">
        <HubChatPanel />
      </div>
    </div>
  );
}
