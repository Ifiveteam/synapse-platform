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
    <header className="flex shrink-0 items-center justify-end gap-1 px-6 pt-5 pb-0 md:px-8">
      <DemoMenu />
      <Button
        variant="ghost"
        size="sm"
        className="text-muted-foreground hover:text-foreground h-8 gap-1.5 rounded-full px-3 text-[12px] font-normal"
        asChild
      >
        <Link to={ROUTES.download}>
          <Download size={13} className="opacity-70" />
          Download
        </Link>
      </Button>
      {user ? (
        <Button
          size="sm"
          variant="ghost"
          className="text-muted-foreground hover:text-foreground h-8 rounded-full px-3 text-[12px] font-normal"
          onClick={logout}
        >
          로그아웃
        </Button>
      ) : (
        <Button
          size="sm"
          variant="ghost"
          className="text-foreground h-8 rounded-full px-3 text-[12px] font-medium"
          onClick={openLoginModal}
        >
          로그인
        </Button>
      )}
    </header>
  );
}
