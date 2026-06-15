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
    <header className="flex shrink-0 items-start justify-between gap-4 px-6 pt-6 pb-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Home</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          {user
            ? `${user.name}님, 오케스트레이터와 대화를 시작해 보세요.`
            : "로그인이 필요합니다. 시작하려면 로그인해 주세요."}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <DemoMenu />
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <Link to={ROUTES.download}>
            <Download size={14} />
            Download
          </Link>
        </Button>
        {user ? (
          <Button size="sm" variant="outline" onClick={logout}>
            로그아웃
          </Button>
        ) : (
          <Button size="sm" onClick={openLoginModal}>
            Sign Up
          </Button>
        )}
      </div>
    </header>
  );
}
