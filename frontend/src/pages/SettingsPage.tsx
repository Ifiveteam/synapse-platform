import { useState, type ReactNode } from "react";
import { toast } from "sonner";
import {
  ChevronRight,
  CreditCard,
  Shield,
  User,
  type LucideIcon,
} from "lucide-react";

import { ProfileEditModal } from "@/components/auth/profile-edit-modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/utils";

type SettingsSection = "billing" | "permissions" | "account";

const SECTIONS: {
  id: SettingsSection;
  label: string;
  description: string;
  icon: LucideIcon;
}[] = [
  {
    id: "billing",
    label: "결제/구독",
    description: "플랜·결제 수단·청구 내역",
    icon: CreditCard,
  },
  {
    id: "permissions",
    label: "권한설정",
    description: "알림·데이터·에이전트 접근",
    icon: Shield,
  },
  {
    id: "account",
    label: "계정설정",
    description: "프로필·보안·로그아웃",
    icon: User,
  },
];

function ToggleRow({
  label,
  description,
  defaultChecked = false,
}: {
  label: string;
  description: string;
  defaultChecked?: boolean;
}) {
  const [checked, setChecked] = useState(defaultChecked);

  return (
    <label className="border-border flex cursor-pointer items-start justify-between gap-4 rounded-xl border bg-card px-4 py-3.5">
      <span className="min-w-0">
        <span className="block text-sm font-medium">{label}</span>
        <span className="text-muted-foreground mt-0.5 block text-xs">
          {description}
        </span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => setChecked(e.target.checked)}
        className="border-border text-primary mt-0.5 size-4 shrink-0 rounded"
      />
    </label>
  );
}

const TOSS_CLIENT_KEY = "test_ck_6BYq7GWPVv9lQoon9GZl3NE5vbo1";
const PLAN_AMOUNT = 19900;

function BillingPanel() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const isPro = user?.plan === "pro";
  const [paying, setPaying] = useState(false);
  const [subModalOpen, setSubModalOpen] = useState(false);
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  async function handlePayment() {
    if (!user) return;
    setPaying(true);
    try {
      const { loadTossPayments } = await import("@tosspayments/tosspayments-sdk");
      const toss = await loadTossPayments(TOSS_CLIENT_KEY);
      const payment = toss.payment({ customerKey: user.id });
      await payment.requestPayment({
        method: "CARD",
        amount: { currency: "KRW", value: PLAN_AMOUNT },
        orderId: `order-${user.id}-${Date.now()}`,
        orderName: "Synapse Pro 플랜",
        successUrl: `${window.location.origin}/payment/success`,
        failUrl: `${window.location.origin}/settings`,
        customerEmail: user.email,
        customerName: user.name,
      });
    } catch {
      setPaying(false);
    }
  }

  async function handleCancel() {
    if (!user) return;
    setCancelling(true);
    try {
      const { cancelSubscription } = await import("@/api/payment");
      const updated = await cancelSubscription();
      if (updated) {
        setUser({ ...user, plan: updated.plan });
        toast.success("구독이 취소되었습니다");
        setCancelConfirmOpen(false);
        setSubModalOpen(false);
      } else {
        toast.error("구독 취소에 실패했습니다");
      }
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* 구독 상세 모달 */}
      {subModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-slate-900/20 backdrop-blur-[2px]"
            onClick={() => setSubModalOpen(false)}
          />
          <div className="relative w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <h2 className="mb-4 text-base font-semibold">구독 정보</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">플랜</span>
                <span className="font-medium">Pro</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">금액</span>
                <span className="font-medium">₩19,900 / 월</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">상태</span>
                <Badge variant="indigo" className="rounded-full text-xs">구독 중</Badge>
              </div>
            </div>

            <div className="border-border my-5 border-t" />

            <div className="flex justify-between gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSubModalOpen(false)}
                disabled={cancelling}
              >
                닫기
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-destructive hover:text-destructive"
                onClick={() => setCancelConfirmOpen(true)}
                disabled={cancelling}
              >
                구독 취소
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 구독 취소 재확인 모달 */}
      {cancelConfirmOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-slate-900/30 backdrop-blur-[2px]"
            onClick={() => !cancelling && setCancelConfirmOpen(false)}
          />
          <div className="relative w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <h2 className="mb-2 text-base font-semibold">정말 취소하시겠습니까?</h2>
            <p className="text-muted-foreground text-sm">
              구독을 취소하면 Pro 플랜 혜택이 즉시 종료됩니다. 이 작업은 되돌릴 수 없습니다.
            </p>

            <div className="mt-5 flex justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCancelConfirmOpen(false)}
                disabled={cancelling}
              >
                아니오
              </Button>
              <Button
                size="sm"
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={handleCancel}
                disabled={cancelling}
              >
                {cancelling ? "취소 중..." : "예, 취소합니다"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="border-border rounded-2xl border bg-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">{isPro ? "Pro 플랜" : "Free 플랜"}</p>
            <p className="text-muted-foreground mt-1 text-sm">
              {isPro ? "월 19,900원 · Pro 이용 중" : "무료 플랜 이용 중"}
            </p>
          </div>
          {isPro ? (
            <Badge variant="indigo" className="rounded-full">구독 중</Badge>
          ) : (
            <Badge variant="outline" className="rounded-full">Free</Badge>
          )}
        </div>
        {isPro ? (
          <Button
            size="sm"
            variant="outline"
            className="mt-4"
            onClick={() => setSubModalOpen(true)}
          >
            구독 관리
          </Button>
        ) : (
          <Button
            size="sm"
            className="mt-4"
            onClick={handlePayment}
            disabled={paying}
          >
            {paying ? "결제창 여는 중..." : "Pro로 업그레이드 · ₩19,900"}
          </Button>
        )}
      </div>
    </div>
  );
}

function PermissionsPanel() {
  return (
    <div className="space-y-3">
      <ToggleRow
        label="이메일 알림"
        description="분석 완료·트렌드 업데이트를 메일로 받습니다."
        defaultChecked
      />
      <ToggleRow
        label="에이전트 데이터 접근"
        description="Profiler·Navigator가 수집 데이터를 분석에 사용합니다."
        defaultChecked
      />
      <ToggleRow
        label="외부 소스 연동"
        description="Indexer가 Drive·RSS 등 외부 소스를 읽을 수 있습니다."
        defaultChecked
      />
      <ToggleRow
        label="익명 통계 공유"
        description="서비스 개선을 위해 비식별 통계를 공유합니다."
      />
    </div>
  );
}

function AccountPanel() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [modalOpen, setModalOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDeleteAccount() {
    if (!user) return;
    setDeleting(true);
    try {
      const { deleteMe } = await import("@/api/auth");
      const ok = await deleteMe();
      if (ok) {
        toast.success("계정이 탈퇴 처리되었습니다");
        logout();
      } else {
        toast.error("탈퇴 처리에 실패했습니다");
      }
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-4">
      <ProfileEditModal open={modalOpen} onClose={() => setModalOpen(false)} />

      {/* 탈퇴 확인 모달 */}
      {deleteConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-slate-900/20 backdrop-blur-[2px]"
            onClick={() => setDeleteConfirmOpen(false)}
          />
          <div className="relative w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <h2 className="mb-2 text-base font-semibold">정말 탈퇴하시겠어요?</h2>
            <p className="text-muted-foreground mb-6 text-sm">
              계정과 모든 데이터가 영구적으로 삭제되며 복구할 수 없습니다.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setDeleteConfirmOpen(false)}
                disabled={deleting}
              >
                취소
              </Button>
              <Button
                size="sm"
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={handleDeleteAccount}
                disabled={deleting}
              >
                {deleting ? "탈퇴 중..." : "탈퇴하기"}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="border-border rounded-2xl border bg-card p-5">
        <p className="mb-4 text-sm font-semibold">프로필</p>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">이름</dt>
            <dd className="font-medium">{user?.name ?? "게스트"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">이메일</dt>
            <dd className="font-medium">{user?.email ?? "—"}</dd>
          </div>
        </dl>
        <Button
          size="sm"
          variant="outline"
          className="mt-4"
          onClick={() => setModalOpen(true)}
        >
          프로필 수정
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <Button
          size="sm"
          variant="outline"
          className="text-destructive hover:text-destructive"
          onClick={logout}
        >
          로그아웃
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="text-muted-foreground hover:text-destructive text-xs"
          onClick={() => setDeleteConfirmOpen(true)}
        >
          탈퇴하기
        </Button>
      </div>
    </div>
  );
}

const PANELS: Record<SettingsSection, () => ReactNode> = {
  billing: BillingPanel,
  permissions: PermissionsPanel,
  account: AccountPanel,
};

export function SettingsPage() {
  const [active, setActive] = useState<SettingsSection>("billing");
  const ActivePanel = PANELS[active];

  return (
    <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-6 py-8">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">설정</h1>

      <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav className="flex flex-col gap-1">
          {SECTIONS.map(({ id, label, description, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActive(id)}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-3 text-left transition-colors",
                active === id
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon size={18} className="shrink-0" />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{label}</span>
                <span className="mt-0.5 block truncate text-xs opacity-80">
                  {description}
                </span>
              </span>
              <ChevronRight size={16} className="shrink-0 opacity-50" />
            </button>
          ))}
        </nav>

        <section className="min-w-0">
          <h2 className="mb-4 text-lg font-semibold">
            {SECTIONS.find((s) => s.id === active)?.label}
          </h2>
          <ActivePanel />
        </section>
      </div>
    </div>
  );
}
