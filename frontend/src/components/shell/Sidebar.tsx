import type { ComponentType, ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bookmark,
  MessageSquare,
  Settings,
  Target,
  User,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";
import { useShellStore } from "@/stores/shell";
import { useSidebarStore } from "@/stores/sidebar";

function BrandLogo({ expanded }: { expanded: boolean }) {
  return (
    <span
      className={cn(
        "bg-primary flex shrink-0 items-center justify-center rounded-lg",
        expanded ? "h-8 w-8" : "h-9 w-9",
      )}
    >
      <span className="text-primary-foreground text-xs font-bold">S</span>
    </span>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-muted-foreground px-3 pt-3 pb-1 text-[10px] font-semibold tracking-widest uppercase">
      {children}
    </p>
  );
}

function SidebarRow({
  icon: Icon,
  label,
  sublabel,
  onClick,
  href,
  active,
  expanded,
}: {
  icon: ComponentType<{ size?: number; className?: string }>;
  label: string;
  sublabel?: string;
  onClick?: () => void;
  href?: string;
  active?: boolean;
  expanded: boolean;
}) {
  const className = cn(
    "flex items-center rounded-xl transition-colors",
    expanded ? "min-h-10 gap-3 px-3 py-2" : "h-9 w-9 justify-center",
    active
      ? "bg-accent text-accent-foreground"
      : "text-muted-foreground hover:bg-secondary hover:text-foreground",
  );

  const content = (
    <>
      <Icon size={16} className="shrink-0" />
      {expanded && (
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{label}</span>
          {sublabel && (
            <span className="text-muted-foreground block truncate text-xs">
              {sublabel}
            </span>
          )}
        </span>
      )}
    </>
  );

  if (href) {
    return (
      <Link to={href} title={label} className={className}>
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick} title={label} className={className}>
      {content}
    </button>
  );
}

export function Sidebar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const expanded = useShellStore((s) => s.sidebarExpanded);
  const setSidebarExpanded = useShellStore((s) => s.setSidebarExpanded);
  const openLoginModal = useShellStore((s) => s.openLoginModal);
  const activeIdealLabel = useSidebarStore((s) => s.activeIdealLabel);
  const scraps = useSidebarStore((s) => s.scraps);
  const chats = useSidebarStore((s) => s.chats);

  const latestScraps = scraps.slice(0, 3);
  const isScrapsSection =
    pathname === ROUTES.scraps || pathname.startsWith(`${ROUTES.scraps}/`);
  const idealLabel = activeIdealLabel ?? "이상향 미설정";

  const handleBrandClick = () => {
    if (!expanded) {
      setSidebarExpanded(true);
      return;
    }
    if (pathname === ROUTES.home) {
      setSidebarExpanded(false);
      return;
    }
    navigate(ROUTES.home);
  };

  return (
    <aside
      className={cn(
        "border-border bg-card flex h-screen shrink-0 flex-col border-r transition-[width] duration-200 ease-in-out",
        expanded ? "w-[260px]" : "w-[60px]",
      )}
    >
      <div
        className={cn(
          "border-border shrink-0 border-b",
          expanded ? "px-3 py-3" : "flex justify-center px-2 py-3",
        )}
      >
        {expanded ? (
          <button
            type="button"
            onClick={handleBrandClick}
            title="홈"
            className="hover:bg-secondary flex w-full min-w-0 items-center gap-2 rounded-xl px-1 py-1 text-left transition-colors"
          >
            <BrandLogo expanded />
            <span className="text-foreground truncate text-sm font-semibold">
              Synapse
            </span>
          </button>
        ) : (
          <button
            type="button"
            onClick={handleBrandClick}
            title="사이드바 펼치기"
            className="hover:opacity-80 transition-opacity"
          >
            <BrandLogo expanded={false} />
          </button>
        )}
      </div>

      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col overflow-hidden",
          expanded ? "" : "items-center gap-1 px-1 pt-2",
        )}
      >
        {/* 유저 정보 */}
        <div className={cn("shrink-0", expanded ? "px-2 pt-2" : "")}>
          {user ? (
            <Link
              to={ROUTES.myAnalyses}
              title="내 분석 목록"
              className={cn(
                "hover:bg-secondary flex w-full items-center rounded-xl transition-colors",
                expanded ? "gap-3 px-3 py-2" : "h-9 w-9 justify-center",
                pathname === ROUTES.myAnalyses && "bg-accent text-accent-foreground",
              )}
            >
              {user.picture ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  width={32}
                  height={32}
                  className="shrink-0 rounded-full"
                />
              ) : (
                <div className="bg-accent text-accent-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold">
                  {user.name[0]}
                </div>
              )}
              {expanded && (
                <span className="min-w-0 truncate text-left text-sm font-medium">
                  {user.name}
                </span>
              )}
            </Link>
          ) : (
            <button
              type="button"
              onClick={openLoginModal}
              title="로그인"
              className={cn(
                "bg-secondary text-muted-foreground hover:bg-accent hover:text-accent-foreground flex items-center rounded-xl transition-colors",
                expanded ? "h-10 w-full gap-3 px-3" : "h-9 w-9 justify-center",
              )}
            >
              <User size={16} className="shrink-0" />
              {expanded && (
                <span className="text-sm font-medium">로그인이 필요합니다</span>
              )}
            </button>
          )}
        </div>

        {/* 적용 중 이상향 */}
        <div className={cn("shrink-0", expanded ? "px-2 pt-1" : "")}>
          <SidebarRow
            expanded={expanded}
            icon={Target}
            label={idealLabel}
            sublabel={expanded ? "현재 적용 중" : undefined}
            href={ROUTES.idealManagement}
            active={pathname === ROUTES.idealManagement}
          />
        </div>

        {/* 스크랩 · 채팅 (펼침 시 스크롤) */}
        <div
          className={cn(
            "min-h-0 flex-1 overflow-y-auto",
            expanded ? "" : "flex flex-col items-center gap-1",
          )}
        >
          {expanded ? (
            <>
              <Link
                to={ROUTES.scraps}
                className={cn(
                  "text-muted-foreground hover:text-foreground mb-1 block px-3 pt-3 pb-1 text-[10px] font-semibold tracking-widest uppercase transition-colors",
                  isScrapsSection && "text-primary",
                )}
              >
                스크랩
              </Link>
              <div className="flex flex-col gap-0.5 px-2 pb-2">
                {latestScraps.length > 0 ? (
                  latestScraps.map((scrap) => (
                    <Link
                      key={scrap.id}
                      to={ROUTES.scraps}
                      title={scrap.title}
                      className="hover:bg-secondary flex items-start gap-2 rounded-xl px-3 py-2 text-left transition-colors"
                    >
                      <Bookmark
                        size={14}
                        className="text-muted-foreground mt-0.5 shrink-0"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                          {scrap.title}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          {scrap.savedAt}
                        </span>
                      </span>
                    </Link>
                  ))
                ) : (
                  <p className="text-muted-foreground px-3 py-2 text-xs">
                    저장된 스크랩이 없습니다
                  </p>
                )}
              </div>

              <SectionLabel>채팅 기록</SectionLabel>
              <div className="flex flex-col gap-0.5 px-2 pb-2">
                {chats.length > 0 ? (
                  chats.map((chat) => (
                    <button
                      key={chat.id}
                      type="button"
                      title={chat.title}
                      className="hover:bg-secondary flex items-start gap-2 rounded-xl px-3 py-2 text-left transition-colors"
                    >
                      <MessageSquare
                        size={14}
                        className="text-muted-foreground mt-0.5 shrink-0"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm">
                          {chat.title}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          {chat.updatedAt}
                        </span>
                      </span>
                    </button>
                  ))
                ) : (
                  <p className="text-muted-foreground px-3 py-2 text-xs">
                    채팅 기록이 없습니다
                  </p>
                )}
              </div>
            </>
          ) : (
            <>
              <SidebarRow
                expanded={false}
                icon={Bookmark}
                label="스크랩"
                href={ROUTES.scraps}
                active={isScrapsSection}
              />
              <SidebarRow
                expanded={false}
                icon={MessageSquare}
                label="채팅 기록"
              />
            </>
          )}
        </div>
      </div>

      {/* 설정 */}
      <div
        className={cn(
          "border-border shrink-0 border-t px-2 py-3",
          expanded ? "" : "flex justify-center",
        )}
      >
        <SidebarRow
          expanded={expanded}
          icon={Settings}
          label="설정"
          href={ROUTES.settings}
          active={pathname.startsWith(ROUTES.settings)}
        />
      </div>
    </aside>
  );
}
