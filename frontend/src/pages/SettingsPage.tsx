import { useState, type ReactNode } from "react";
import {
  ChevronRight,
  CreditCard,
  Shield,
  User,
  type LucideIcon,
} from "lucide-react";

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

function BillingPanel() {
  return (
    <div className="space-y-4">
      <div className="border-border rounded-2xl border bg-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Pro 플랜</p>
            <p className="text-muted-foreground mt-1 text-sm">
              월 19,900원 · 다음 결제일 2025.07.14
            </p>
          </div>
          <Badge variant="indigo" className="rounded-full">
            구독 중
          </Badge>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" variant="outline">
            플랜 변경
          </Button>
          <Button size="sm" variant="outline">
            결제 수단 관리
          </Button>
        </div>
      </div>

      <div className="border-border rounded-2xl border bg-card p-5">
        <p className="mb-3 text-sm font-semibold">최근 청구</p>
        <ul className="divide-border divide-y text-sm">
          {[
            { date: "2025.06.14", amount: "₩19,900", status: "결제 완료" },
            { date: "2025.05.14", amount: "₩19,900", status: "결제 완료" },
          ].map((row) => (
            <li
              key={row.date}
              className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <span className="text-muted-foreground">{row.date}</span>
              <span className="font-medium">{row.amount}</span>
              <span className="text-muted-foreground text-xs">{row.status}</span>
            </li>
          ))}
        </ul>
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

  return (
    <div className="space-y-4">
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
        <Button size="sm" variant="outline" className="mt-4">
          프로필 수정
        </Button>
      </div>

      <div className="border-border rounded-2xl border bg-card p-5">
        <p className="mb-2 text-sm font-semibold">보안</p>
        <p className="text-muted-foreground mb-4 text-xs">
          비밀번호 변경 및 2단계 인증을 관리합니다.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline">
            비밀번호 변경
          </Button>
          <Button size="sm" variant="outline">
            2단계 인증 설정
          </Button>
        </div>
      </div>

      <Button
        size="sm"
        variant="outline"
        className="text-destructive hover:text-destructive"
        onClick={logout}
      >
        로그아웃
      </Button>
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
