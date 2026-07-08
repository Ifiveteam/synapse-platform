import { type ComponentType, type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  Bookmark,
  Menu,
  MessageSquare,
  Moon,
  Pencil,
  Settings,
  Sun,
  Target,
  Trash2,
  User,
} from "lucide-react";

import { deleteSession } from "@/api/curator";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";
import { getAnalysisChatStore, useChatStore } from "@/stores/chat";
import { useShellStore } from "@/stores/shell";
import { formatRelativeTime, useSidebarStore } from "@/stores/sidebar";
import { useThemeStore } from "@/stores/theme";
import logoUrl from "@/assets/logo.png";

function ThemeToggle({ expanded }: { expanded: boolean }) {
  const { theme, toggle } = useThemeStore();
  const isDark = theme === "dark";

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={toggle}
        title={isDark ? "라이트 모드" : "다크 모드"}
        className="text-muted-foreground hover:text-foreground hover:bg-secondary flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-colors"
      >
        {isDark ? <Sun size={15} /> : <Moon size={15} />}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2">
      <Moon size={14} className="text-muted-foreground shrink-0" />
      <button
        type="button"
        role="switch"
        aria-checked={isDark}
        onClick={toggle}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200",
          isDark ? "bg-primary" : "bg-muted",
        )}
      >
        <span
          className={cn(
            "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200",
            isDark ? "translate-x-4" : "translate-x-0",
          )}
        />
      </button>
      <Sun size={14} className="text-muted-foreground shrink-0" />
    </div>
  );
}

function BrandLogo({ expanded }: { expanded: boolean }) {
  const { theme } = useThemeStore();
  return (
    <img
      src={logoUrl}
      alt="Synapse"
      className={cn(
        "shrink-0 object-contain",
        expanded ? "h-8 w-8" : "h-9 w-9",
        theme === "dark" && "invert brightness-200",
      )}
    />
  );
}

export function UserAvatar({
  picture,
  name,
  size,
}: {
  picture?: string | null;
  name: string;
  size: number;
}) {
  const { theme } = useThemeStore();
  const [failed, setFailed] = useState(false);

  // 사진이 없거나 로드 실패(구글 아바타 ORB 차단 등) 시 Synapse 로고로 폴백
  if (!picture || failed) {
    return (
      <img
        src={logoUrl}
        alt={name}
        width={size}
        height={size}
        className={cn(
          "shrink-0 object-contain",
          theme === "dark" && "invert brightness-200",
        )}
      />
    );
  }

  return (
    <img
      src={picture}
      alt={name}
      width={size}
      height={size}
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className="shrink-0 rounded-full object-cover"
    />
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
      <Icon size={15} className="shrink-0" />
      {expanded && (
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-medium">{label}</span>
          {sublabel && (
            <span className="text-muted-foreground block truncate text-[10px]">
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
  const clearChats = useSidebarStore((s) => s.clearChats);
  const analysisChats = useSidebarStore((s) => s.analysisChats);
  const renameAnalysisChat = useSidebarStore((s) => s.renameAnalysisChat);
  const removeAnalysisChat = useSidebarStore((s) => s.removeAnalysisChat);
  const clearMessages = useChatStore((s) => s.clearMessages);

  useEffect(() => {
    if (!user) {
      clearChats();
      clearMessages();
    }
  }, [user, clearChats, clearMessages]);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  const startEdit = useCallback((analysisId: string, currentTitle: string) => {
    setEditingId(analysisId);
    setEditValue(currentTitle);
    setTimeout(() => editInputRef.current?.focus(), 0);
  }, []);

  const commitEdit = useCallback(() => {
    if (editingId && editValue.trim()) renameAnalysisChat(editingId, editValue.trim());
    setEditingId(null);
  }, [editingId, editValue, renameAnalysisChat]);

  const handleDeleteChat = useCallback(async (analysisId: string) => {
    const analysisChatStore = getAnalysisChatStore(analysisId);
    const oldSessionId = analysisChatStore.getState().sessionId;
    analysisChatStore.getState().clearMessages();
    removeAnalysisChat(analysisId);
    try { await deleteSession(oldSessionId); } catch { /* ignore */ }
  }, [removeAnalysisChat]);

  const chatHistoryItems = Object.entries(analysisChats)
    .map(([analysisId, meta]) => ({
      analysisId,
      title: meta.title,
      updatedAt: meta.updatedAt,
    }))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());

  const isScrapsSection =
    pathname === ROUTES.scraps || pathname.startsWith(`${ROUTES.scraps}/`);

  const handleBrandClick = () => {
    if (!expanded) {
      setSidebarExpanded(true);
      return;
    }
    // 큐레이터 대화를 리셋하고 깨끗한 첫 홈으로 이동
    clearMessages();
    navigate(ROUTES.home);
  };

  return (
    <aside
      className={cn(
        "border-border bg-card flex h-screen shrink-0 flex-col border-r transition-[width] duration-200 ease-in-out",
        expanded ? "w-[220px]" : "w-[52px]",
      )}
    >
      <div
        className={cn(
          "border-border shrink-0 border-b",
          expanded ? "px-3 py-3" : "flex justify-center px-2 py-3",
        )}
      >
        {expanded ? (
          <div className="flex w-full min-w-0 items-center gap-1">
            <button
              type="button"
              onClick={handleBrandClick}
              title="홈"
              className="hover:bg-secondary flex min-w-0 flex-1 items-center gap-2 rounded-xl px-1 py-1 text-left transition-colors"
            >
              <BrandLogo expanded />
              <span className="text-foreground truncate text-sm font-semibold">
                Synapse
              </span>
            </button>
            <button
              type="button"
              onClick={() => setSidebarExpanded(false)}
              title="사이드바 접기"
              className="text-muted-foreground hover:text-foreground hover:bg-secondary flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-colors"
            >
              <Menu size={16} />
            </button>
          </div>
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
              to={ROUTES.ME.HOME}
              title="내 정보"
              className={cn(
                "hover:bg-secondary flex w-full items-center rounded-xl transition-colors",
                expanded ? "gap-3 px-3 py-2" : "h-9 w-9 justify-center",
                pathname === ROUTES.ME.HOME && "bg-accent text-accent-foreground",
              )}
            >
              <UserAvatar picture={user.picture} name={user.name} size={32} />
              {expanded && (
                <span className="flex min-w-0 flex-1 items-center gap-1.5">
                  {activeIdealLabel && (
                    <Target
                      size={12}
                      className="text-muted-foreground shrink-0"
                    />
                  )}
                  <span className="truncate text-left text-sm font-medium">
                    {activeIdealLabel ?? user.name}
                  </span>
                  {user.plan === "pro" && (
                    <span className="shrink-0 rounded-full bg-indigo-500 px-1.5 py-0.5 text-[10px] font-bold text-white leading-none">
                      Pro
                    </span>
                  )}
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

        {/* 활동 이력 */}
        <div
          className={cn(
            "shrink-0 flex flex-col gap-0.5",
            expanded ? "px-2 pt-1" : "items-center",
          )}
        >
          <SidebarRow
            expanded={expanded}
            icon={Activity}
            label="활동 이력"
            href={ROUTES.ME.ACTIVITY}
            active={pathname === ROUTES.ME.ACTIVITY}
          />
          <SidebarRow
            expanded={expanded}
            icon={Bookmark}
            label="스크랩"
            href={ROUTES.scraps}
            active={isScrapsSection}
          />
        </div>

        {/* 채팅 기록 (펼침 시 스크롤) */}
        <div
          className={cn(
            "min-h-0 flex-1 overflow-y-auto",
            expanded ? "" : "flex flex-col items-center gap-1",
          )}
        >
          {expanded ? (
            <>
              <SectionLabel>채팅 기록</SectionLabel>
              <div className="flex flex-col gap-0.5 px-2 pb-2">
                {chatHistoryItems.length > 0 ? (
                  chatHistoryItems.map((item) => (
                    <div
                      key={item.analysisId}
                      className="group relative flex items-center rounded-xl transition-colors hover:bg-secondary"
                    >
                      {editingId === item.analysisId ? (
                        <div className="flex flex-1 items-center gap-2 px-3 py-2">
                          <MessageSquare size={14} className="text-muted-foreground shrink-0" />
                          <input
                            ref={editInputRef}
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={commitEdit}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") commitEdit();
                              if (e.key === "Escape") setEditingId(null);
                            }}
                            className="flex-1 bg-transparent text-xs outline-none"
                          />
                        </div>
                      ) : (
                        <Link
                          to={ROUTES.analysisDetail(item.analysisId)}
                          title={item.title}
                          className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left"
                        >
                          <MessageSquare size={14} className="text-muted-foreground shrink-0" />
                          <span className="min-w-0 flex-1 truncate text-xs">{item.title}</span>
                          <span className="text-muted-foreground shrink-0 text-[10px] group-hover:opacity-0">
                            {formatRelativeTime(item.updatedAt)}
                          </span>
                        </Link>
                      )}

                      {editingId !== item.analysisId && (
                        <div className="absolute right-1.5 hidden shrink-0 items-center gap-0.5 group-hover:flex">
                          <button
                            type="button"
                            title="제목 수정"
                            onClick={(e) => { e.stopPropagation(); startEdit(item.analysisId, item.title); }}
                            className="text-muted-foreground hover:text-foreground flex h-6 w-6 items-center justify-center rounded-lg transition-colors hover:bg-background"
                          >
                            <Pencil size={11} />
                          </button>
                          <button
                            type="button"
                            title="삭제"
                            onClick={(e) => { e.stopPropagation(); void handleDeleteChat(item.analysisId); }}
                            className="text-muted-foreground hover:text-destructive flex h-6 w-6 items-center justify-center rounded-lg transition-colors hover:bg-background"
                          >
                            <Trash2 size={11} />
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground px-3 py-2 text-xs">
                    {user ? "채팅 기록이 없습니다" : "로그인 후 이용해주세요"}
                  </p>
                )}
              </div>
            </>
          ) : (
            <SidebarRow
              expanded={false}
              icon={MessageSquare}
              label="채팅 기록"
            />
          )}
        </div>
      </div>

      {/* 설정 · 테마 */}
      <div
        className={cn(
          "border-border shrink-0 border-t px-2 py-3",
          expanded ? "flex items-center gap-1" : "flex flex-col items-center gap-1",
        )}
      >
        <div className={cn(expanded ? "flex-1" : "")}>
          <Link
            to={ROUTES.settings}
            title="설정"
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-xl transition-colors",
              pathname.startsWith(ROUTES.settings)
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            )}
          >
            <Settings size={15} className="shrink-0" />
          </Link>
        </div>
        <ThemeToggle expanded={expanded} />
      </div>
    </aside>
  );
}
