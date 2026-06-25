import { type ComponentType, type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bookmark,
  MessageSquare,
  Moon,
  Pencil,
  Settings,
  Sun,
  Target,
  Trash2,
  User,
} from "lucide-react";

import { deleteSession, fetchSessionMessages } from "@/api/curator";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import { useShellStore } from "@/stores/shell";
import { useSidebarStore } from "@/stores/sidebar";
import { useThemeStore } from "@/stores/theme";

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
      src="/src/assets/logo.png"
      alt="Synapse"
      className={cn(
        "shrink-0 object-contain",
        expanded ? "h-8 w-8" : "h-9 w-9",
        theme === "dark" && "invert brightness-200",
      )}
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
  const scraps = useSidebarStore((s) => s.scraps);
  const chats = useSidebarStore((s) => s.chats);
  const setSession = useChatStore((s) => s.setSession);
  const currentSessionId = useChatStore((s) => s.sessionId);
  const cachedSessions = useChatStore((s) => s.sessions);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const renameChat = useSidebarStore((s) => s.renameChat);
  const deleteChat = useSidebarStore((s) => s.deleteChat);
  const clearChats = useSidebarStore((s) => s.clearChats);

  useEffect(() => {
    if (!user) {
      clearChats();
      clearMessages();
    }
  }, [user, clearChats, clearMessages]);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  const startEdit = useCallback((id: string, currentTitle: string) => {
    setEditingId(id);
    setEditValue(currentTitle);
    setTimeout(() => editInputRef.current?.focus(), 0);
  }, []);

  const commitEdit = useCallback(() => {
    if (editingId && editValue.trim()) renameChat(editingId, editValue.trim());
    setEditingId(null);
  }, [editingId, editValue, renameChat]);

  const handleDeleteChat = useCallback(async (id: string) => {
    deleteChat(id);
    if (id === currentSessionId) clearMessages();
    try { await deleteSession(id); } catch { /* ignore */ }
  }, [deleteChat, clearMessages, currentSessionId]);

  const handleChatClick = useCallback(async (sessionId: string) => {
    // 이미 캐시된 세션이면 DB 요청 없이 바로 전환
    if (cachedSessions[sessionId]?.length) {
      setSession(sessionId, cachedSessions[sessionId]);
      navigate(ROUTES.home);
      return;
    }
    try {
      const items = await fetchSessionMessages(sessionId);
      setSession(
        sessionId,
        items.map((m) => ({
          id: Math.random().toString(36).slice(2, 10),
          role: m.role,
          content: m.content,
        })),
      );
      navigate(ROUTES.home);
    } catch {
      // 네트워크 오류 등 무시
    }
  }, [setSession, navigate, cachedSessions]);

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
                <span className="flex min-w-0 flex-1 items-center gap-1.5 truncate">
                  <span className="truncate text-left text-sm font-medium">
                    {user.name}
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
                        <span className="block truncate text-xs">
                          {scrap.title}
                        </span>
                        <span className="text-muted-foreground text-[10px]">
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
                    <div
                      key={chat.id}
                      className="group relative flex items-center rounded-xl transition-colors hover:bg-secondary"
                    >
                      {editingId === chat.id ? (
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
                        <button
                          type="button"
                          title={chat.title}
                          onClick={() => void handleChatClick(chat.id)}
                          className="flex min-w-0 flex-1 items-start gap-2 px-3 py-2 text-left"
                        >
                          <MessageSquare size={14} className="text-muted-foreground mt-0.5 shrink-0" />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-xs">{chat.title}</span>
                            <span className="text-muted-foreground text-[10px]">{chat.updatedAt}</span>
                          </span>
                        </button>
                      )}

                      {editingId !== chat.id && (
                        <div className="absolute right-1.5 hidden shrink-0 items-center gap-0.5 group-hover:flex">
                          <button
                            type="button"
                            title="제목 수정"
                            onClick={(e) => { e.stopPropagation(); startEdit(chat.id, chat.title); }}
                            className="text-muted-foreground hover:text-foreground flex h-6 w-6 items-center justify-center rounded-lg transition-colors hover:bg-background"
                          >
                            <Pencil size={11} />
                          </button>
                          <button
                            type="button"
                            title="삭제"
                            onClick={(e) => { e.stopPropagation(); void handleDeleteChat(chat.id); }}
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
          expanded ? "flex items-center gap-1" : "flex flex-col items-center gap-1",
        )}
      >
        <div className={cn(expanded ? "flex-1" : "")}>
          <SidebarRow
            expanded={expanded}
            icon={Settings}
            label="설정"
            href={ROUTES.settings}
            active={pathname.startsWith(ROUTES.settings)}
          />
        </div>
        <ThemeToggle expanded={expanded} />
      </div>
    </aside>
  );
}
