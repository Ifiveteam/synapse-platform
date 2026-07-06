import { useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Settings, Target } from "lucide-react";

import { ProfileEditModal } from "@/components/auth/profile-edit-modal";
import { UserAvatar } from "@/components/shell/Sidebar";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";
import { useSidebarStore } from "@/stores/sidebar";

/**
 * /me 허브 좌측 계정 패널.
 * 기본 프로필(useAuthStore)과 현재 적용 중인 이상향(sidebar store)을 표시한다.
 */
export function AccountSidePanel() {
  const user = useAuthStore((s) => s.user);
  const activeIdealLabel = useSidebarStore((s) => s.activeIdealLabel);
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <ProfileEditModal open={modalOpen} onClose={() => setModalOpen(false)} />

      {/* 프로필 */}
      <div className="border-border bg-card rounded-2xl border p-5">
        <div className="flex items-center gap-3">
          <UserAvatar
            picture={user?.picture}
            name={user?.name ?? "게스트"}
            size={44}
          />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <p className="truncate text-sm font-semibold">
                {user?.name ?? "게스트"}
              </p>
              {user?.plan === "pro" && (
                <span className="shrink-0 rounded-full bg-indigo-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                  Pro
                </span>
              )}
            </div>
            <p className="text-muted-foreground truncate text-xs">
              {user?.email ?? "—"}
            </p>
          </div>
        </div>

        <Button
          size="sm"
          variant="outline"
          className="mt-4 w-full"
          onClick={() => setModalOpen(true)}
        >
          프로필 수정
        </Button>
      </div>

      {/* 현재 적용 중인 이상향 */}
      <div className="border-border bg-card rounded-2xl border p-5">
        <p className="text-muted-foreground mb-3 text-xs font-medium">
          현재 적용 중인 이상향
        </p>
        <div className="flex items-center gap-3">
          <div className="bg-accent text-accent-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
            <Target size={20} />
          </div>
          <p className="min-w-0 truncate text-sm font-semibold">
            {activeIdealLabel ?? "이상향 미설정"}
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="mt-4 w-full"
          asChild
        >
          <Link to={ROUTES.idealManagement}>이상향 관리</Link>
        </Button>
      </div>

      {/* 바로가기 */}
      <div className="flex flex-col gap-1">
        <Link
          to={ROUTES.ME.ACTIVITY}
          className="text-muted-foreground hover:bg-secondary hover:text-foreground flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors"
        >
          <Activity size={16} className="shrink-0" />
          활동 이력
        </Link>
        <Link
          to={ROUTES.settings}
          className="text-muted-foreground hover:bg-secondary hover:text-foreground flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors"
        >
          <Settings size={16} className="shrink-0" />
          설정
        </Link>
      </div>
    </div>
  );
}
