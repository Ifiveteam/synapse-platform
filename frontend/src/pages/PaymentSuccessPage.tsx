import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { confirmPayment } from "@/api/payment";
import { useAuthStore } from "@/stores/auth";
import { ROUTES } from "@/routes";

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const user = useAuthStore((s) => s.user);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const paymentKey = searchParams.get("paymentKey");
    const orderId = searchParams.get("orderId");
    const amount = Number(searchParams.get("amount"));

    if (!paymentKey || !orderId || !amount || !user) {
      setStatus("error");
      return;
    }

    confirmPayment({ paymentKey, orderId, amount })
      .then((updated) => {
        if (updated && user) {
          setUser({ ...user, plan: updated.plan });
          setStatus("success");
          toast.success("Pro 플랜으로 업그레이드되었습니다!");
          setTimeout(() => navigate(ROUTES.settings), 1500);
        } else {
          setStatus("error");
          toast.error("결제 확인에 실패했습니다");
        }
      })
      .catch(() => setStatus("error"));
  }, [searchParams, user, setUser, navigate]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      {status === "loading" && (
        <>
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground text-sm">결제 확인 중...</p>
        </>
      )}
      {status === "success" && (
        <>
          <div className="text-4xl">🎉</div>
          <p className="text-lg font-semibold">Pro 플랜으로 업그레이드 완료!</p>
          <p className="text-muted-foreground text-sm">설정 페이지로 이동합니다...</p>
        </>
      )}
      {status === "error" && (
        <>
          <div className="text-4xl">⚠️</div>
          <p className="text-lg font-semibold">결제 확인 실패</p>
          <button
            type="button"
            className="text-primary text-sm underline"
            onClick={() => navigate(ROUTES.settings)}
          >
            설정으로 돌아가기
          </button>
        </>
      )}
    </div>
  );
}
