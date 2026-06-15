import { useEffect } from "react";
import { X } from "lucide-react";

import { LoginPanel } from "@/components/auth/login-panel";
import { useShellStore } from "@/stores/shell";

export function LoginModal() {
  const open = useShellStore((s) => s.loginModalOpen);
  const closeLoginModal = useShellStore((s) => s.closeLoginModal);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeLoginModal();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, closeLoginModal]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="닫기"
        className="absolute inset-0 bg-slate-900/20 backdrop-blur-[2px]"
        onClick={closeLoginModal}
      />
      <div className="relative w-full max-w-md">
        <button
          type="button"
          onClick={closeLoginModal}
          className="text-muted-foreground hover:text-foreground hover:bg-secondary absolute -top-3 -right-3 z-10 flex size-8 items-center justify-center rounded-full bg-card shadow-md transition-colors"
          aria-label="닫기"
        >
          <X size={16} />
        </button>
        <LoginPanel />
      </div>
    </div>
  );
}
