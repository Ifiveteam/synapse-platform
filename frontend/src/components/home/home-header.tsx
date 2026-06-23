import { Link } from "react-router-dom";
import { Download } from "lucide-react";

import { DemoMenu } from "@/components/home/demo-menu";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";
import { useShellStore } from "@/stores/shell";

export function HomeHeader() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const openLoginModal = useShellStore((s) => s.openLoginModal);

  return (
    <header className="flex shrink-0 items-center justify-between gap-4 px-6 pt-4 pb-2">
      <p className="text-muted-foreground text-xs">
        {user
          ? `${user.name}님, 오케스트레이터와 대화를 시작해 보세요.`
          : "로그인이 필요합니다. 시작하려면 로그인해 주세요."}
      </p>

      <div className="flex shrink-0 items-center gap-1.5">
        <DemoMenu />
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground h-7 gap-1.5 px-2.5 text-xs"
          asChild
        >
          <Link to={ROUTES.download}>
            <Download size={13} />
            Download
          </Link>
        </Button>
        {user ? (
          <Button
            size="sm"
            variant="ghost"
            className="text-muted-foreground hover:text-foreground h-7 px-2.5 text-xs"
            onClick={logout}
          >
            로그아웃
          </Button>
        ) : (
          <Button size="sm" className="h-7 px-3 text-xs" onClick={openLoginModal}>
            로그인
          </Button>
        )}
      </div>
    </header>
  );
}
