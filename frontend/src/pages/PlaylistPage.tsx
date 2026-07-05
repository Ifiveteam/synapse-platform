import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpDown,
  Check,
  ChevronDown,
  ListVideo,
  Pencil,
  Plus,
  RefreshCw,
  Send,
  Target,
  Trash2,
  X,
  Youtube,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  createPlaylist,
  deletePlaylist,
  getPlaylist,
  listIdeals,
  listPlaylists,
  refreshPlaylistItem,
  regeneratePlaylist,
  renamePlaylist,
  savePlaylistToYoutube,
  setPlaylistPeriod,
  streamPlaylistChat,
} from "@/api/navigator";
import { connectYoutube } from "@/lib/youtube-connect";
import type {
  IdealResponse,
  PlaylistPeriod,
  PlaylistResponse,
  PlaylistSummary,
} from "@/api/types/navigator";
import { IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";

type Row = PlaylistSummary & { idealId: string; idealLabel: string };

/** 재생목록 갱신 주기 (UI 선택값 — 백엔드 연동은 추후) */
const PERIOD_OPTIONS = [
  { value: "none", label: "없음" },
  { value: "daily", label: "매일" },
  { value: "weekly", label: "매주" },
  { value: "monthly", label: "매월" },
] as const;
type PeriodValue = (typeof PERIOD_OPTIONS)[number]["value"];

/** 영상 발행일(ISO) → "YYYY.MM.DD". 값 없거나 파싱 실패면 빈 문자열. */
function formatPubDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())}`;
}

/** 채팅 메시지가 "이 재생목록을 유튜브에 저장/올려줘" 의도인지.
 * 편집 요청("유튜브에서 인기영상 넣어줘", "유튜브 영상 넣어줘")과 헷갈리지 않도록,
 * **목적지 표현 "유튜브에" + 저장 동사**가 바로 이어질 때만 인정하고 "유튜브에서"는 제외한다. */
function isSaveToYoutubeIntent(msg: string): boolean {
  const m = msg.replace(/\s+/g, "");
  if (/(유튜브|유투브|youtube)에서/i.test(m)) return false; // 출처 표현 → 편집
  return /(유튜브|유투브|youtube)에(다가?)?(저장|올려|올릴|담아|담을|넣어|넣을|등록|백업)/i.test(
    m,
  );
}

/** 토글(세그먼트) 버튼 공통 스타일 */
function pillClass(active: boolean) {
  return cn(
    "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors",
    active
      ? "border-primary bg-primary/10 text-primary"
      : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
  );
}

/** 이상향 선택 드롭다운 (검색 가능) */
function IdealSelect({
  ideals,
  value,
  onChange,
  labelOf,
}: {
  ideals: IdealResponse[];
  value: string | null;
  onChange: (id: string) => void;
  labelOf: (i: IdealResponse) => string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = ideals.find((i) => i.id === value) ?? null;
  const q = query.trim().toLowerCase();
  const filtered = q
    ? ideals.filter((i) => labelOf(i).toLowerCase().includes(q))
    : ideals;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="border-border bg-background hover:border-primary/40 flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm transition-colors"
      >
        <span className={selected ? "" : "text-muted-foreground"}>
          {selected ? labelOf(selected) : "이상향 선택"}
        </span>
        <ChevronDown
          size={16}
          className={cn(
            "text-muted-foreground shrink-0 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="border-border bg-card absolute z-20 mt-1 w-full overflow-hidden rounded-lg border shadow-xl">
            <div className="border-border border-b p-2">
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="이상향 검색…"
                className="border-border bg-background focus:border-primary/50 w-full rounded-md border px-2.5 py-1.5 text-sm outline-none"
              />
            </div>
            <ul className="max-h-56 overflow-y-auto p-1">
              {filtered.length === 0 ? (
                <li className="text-muted-foreground px-2.5 py-2 text-sm">
                  검색 결과가 없어요.
                </li>
              ) : (
                filtered.map((i) => (
                  <li key={i.id}>
                    <button
                      type="button"
                      onClick={() => {
                        onChange(i.id);
                        setOpen(false);
                        setQuery("");
                      }}
                      className={cn(
                        "hover:bg-accent flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors",
                        i.id === value && "bg-accent",
                      )}
                    >
                      <Target size={14} className="text-muted-foreground shrink-0" />
                      <span className="flex-1 truncate">{labelOf(i)}</span>
                      {i.id === value && (
                        <Check size={14} className="text-primary shrink-0" />
                      )}
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

export function PlaylistPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialIdeal = searchParams.get("ideal") ?? "all";

  const [ideals, setIdeals] = useState<IdealResponse[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterIdeal, setFilterIdeal] = useState<string>(initialIdeal);
  const [sortDesc, setSortDesc] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  // 새 재생목록 팝업 선택값 (토글)
  const [pickIdealId, setPickIdealId] = useState<string | null>(null);
  const [pickPeriod, setPickPeriod] = useState<PeriodValue>("none");

  // 상세
  const [selected, setSelected] = useState<PlaylistResponse | null>(null);
  // 채팅으로 방금 바뀐(추가된) 영상 id — 커서 올리기 전까지 테두리 강조
  const [changedIds, setChangedIds] = useState<Set<string>>(() => new Set());
  const [refreshingId, setRefreshingId] = useState<string | null>(null);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatLog, setChatLog] = useState<
    { role: "user" | "assistant"; text: string }[]
  >([]);
  const [chatting, setChatting] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const idealLabel = useCallback(
    (i: IdealResponse) => i.persona_label || IDEAL_TYPE_LABEL[i.ideal_type],
    [],
  );

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const idealList = await listIdeals();
      setIdeals(idealList);
      const perIdeal = await Promise.all(
        idealList.map((i) =>
          listPlaylists(i.id)
            .then((ps) =>
              ps.map((p) => ({
                ...p,
                idealId: i.id,
                idealLabel: idealLabel(i),
              })),
            )
            .catch(() => [] as Row[]),
        ),
      );
      setRows(perIdeal.flat());
    } finally {
      setLoading(false);
    }
  }, [idealLabel]);

  useEffect(() => {
    void loadAll();
    return () => abortRef.current?.abort();
  }, [loadAll]);

  // 생성중(pending)인 재생목록을 폴링해 완료되면 자동으로 채운다
  useEffect(() => {
    if (!selected || selected.status !== "pending") return;
    const id = selected.id;
    const timer = setInterval(async () => {
      try {
        const updated = await getPlaylist(id);
        setSelected((cur) => (cur && cur.id === id ? updated : cur));
        setRows((prev) =>
          prev.map((r) =>
            r.id === id
              ? {
                  ...r,
                  status: updated.status,
                  item_count: updated.items.length,
                  title: updated.title,
                }
              : r,
          ),
        );
        if (updated.status !== "pending") clearInterval(timer);
      } catch {
        /* 일시 오류는 무시하고 계속 폴링 */
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [selected?.id, selected?.status]);

  // YouTube 저장중(saving)을 폴링해 완료되면 반영
  useEffect(() => {
    if (!selected || selected.save_status !== "saving") return;
    const id = selected.id;
    const timer = setInterval(async () => {
      try {
        const updated = await getPlaylist(id);
        setSelected((cur) => (cur && cur.id === id ? updated : cur));
        setRows((prev) =>
          prev.map((r) =>
            r.id === id
              ? {
                  ...r,
                  save_status: updated.save_status,
                  youtube_playlist_id: updated.youtube_playlist_id,
                }
              : r,
          ),
        );
        if (updated.save_status !== "saving") clearInterval(timer);
      } catch {
        /* 무시하고 계속 폴링 */
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [selected?.id, selected?.save_status]);

  const visibleRows = useMemo(() => {
    const filtered =
      filterIdeal === "all"
        ? rows
        : rows.filter((r) => r.idealId === filterIdeal);
    return [...filtered].sort((a, b) => {
      const ta = Date.parse(a.created_at);
      const tb = Date.parse(b.created_at);
      return sortDesc ? tb - ta : ta - tb;
    });
  }, [rows, filterIdeal, sortDesc]);

  const onFilterChange = (value: string) => {
    setFilterIdeal(value);
    setSelected(null);
    if (value === "all") setSearchParams({});
    else setSearchParams({ ideal: value });
  };

  const openPlaylist = async (playlistId: string) => {
    setChatLog([]);
    setChangedIds(new Set());
    setSelected(await getPlaylist(playlistId));
  };

  const createFor = async (idealId: string) => {
    setShowPicker(false);
    setCreating(true);
    try {
      const created = await createPlaylist(idealId, pickPeriod);
      const i = ideals.find((x) => x.id === idealId);
      setRows((prev) => [
        {
          id: created.id,
          title: created.title,
          item_count: created.items.length,
          status: created.status,
          save_status: created.save_status,
          refresh_period: created.refresh_period,
          youtube_playlist_id: created.youtube_playlist_id,
          created_at: created.created_at,
          idealId,
          idealLabel: i ? idealLabel(i) : "",
        },
        ...prev,
      ]);
      setChatLog([]);
      setSelected(created); // pending → 폴링이 채움
    } finally {
      setCreating(false);
    }
  };

  const handleSetPeriod = async (id: string, period: PlaylistPeriod) => {
    // 낙관적 반영 (실패해도 다음 로드에서 정정)
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, refresh_period: period } : r)),
    );
    setSelected((cur) =>
      cur && cur.id === id ? { ...cur, refresh_period: period } : cur,
    );
    try {
      await setPlaylistPeriod(id, period);
    } catch {
      /* 무시 */
    }
  };

  const handleNewClick = () => {
    // 필터에 특정 이상향이 잡혀있으면 그걸 기본 선택, "모든 이상향"이면 미선택으로 시작
    setPickIdealId(filterIdeal !== "all" ? filterIdeal : null);
    setPickPeriod("none");
    setShowPicker((v) => !v);
  };

  const handleCreateFromPicker = () => {
    if (!pickIdealId) return;
    // 주기(pickPeriod)는 현재 UI 선택값 — 백엔드 연동은 추후.
    void createFor(pickIdealId);
  };

  const handleRefreshItem = async (videoId: string) => {
    if (!selected) return;
    setRefreshingId(videoId);
    try {
      setSelected(await refreshPlaylistItem(selected.id, videoId));
    } finally {
      setRefreshingId(null);
    }
  };

  const handleRefreshAll = async () => {
    if (!selected || refreshingAll) return;
    setRefreshingAll(true);
    try {
      setChangedIds(new Set());
      setSelected(await regeneratePlaylist(selected.id));
    } finally {
      setRefreshingAll(false);
    }
  };

  const markSaving = (id: string) => {
    setSelected((cur) =>
      cur && cur.id === id ? { ...cur, save_status: "saving" } : cur,
    );
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, save_status: "saving" } : r)),
    );
  };

  const handleSaveYoutube = async (): Promise<boolean> => {
    if (!selected) return false;
    const id = selected.id;
    try {
      let res = await savePlaylistToYoutube(id);
      if (res.needs_reconsent) {
        try {
          await connectYoutube(); // youtube 스코프 동의 팝업
        } catch {
          return false; // 동의 취소
        }
        res = await savePlaylistToYoutube(id);
        if (res.needs_reconsent) return false;
      }
      markSaving(id); // 폴링이 완료를 채움
      return true;
    } catch {
      window.alert("저장을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
      return false;
    }
  };

  const handleDelete = async () => {
    if (!selected || !window.confirm("이 재생목록을 삭제할까요?")) return;
    const deletedId = selected.id;
    await deletePlaylist(deletedId);
    setRows((prev) => prev.filter((r) => r.id !== deletedId));
    setSelected(null);
  };

  const handleDeleteRow = async (playlistId: string) => {
    if (!window.confirm("이 재생목록을 삭제할까요?")) return;
    await deletePlaylist(playlistId);
    setRows((prev) => prev.filter((r) => r.id !== playlistId));
    if (selected?.id === playlistId) setSelected(null);
  };

  const handleRename = async () => {
    if (!selected || !titleDraft.trim()) {
      setEditingTitle(false);
      return;
    }
    const updated = await renamePlaylist(selected.id, titleDraft.trim());
    setSelected(updated);
    setRows((prev) =>
      prev.map((r) => (r.id === updated.id ? { ...r, title: updated.title } : r)),
    );
    setEditingTitle(false);
  };

  const setLastAssistant = (text: string) =>
    setChatLog((prev) => {
      const copy = [...prev];
      for (let i = copy.length - 1; i >= 0; i--) {
        if (copy[i].role === "assistant") {
          copy[i] = { ...copy[i], text };
          break;
        }
      }
      return copy;
    });

  const handleChat = async () => {
    if (!selected || !chatInput.trim() || chatting) return;
    const message = chatInput.trim();

    // "유튜브에 넣어줘" 의도면 편집 대신 저장 로직 실행
    if (isSaveToYoutubeIntent(message)) {
      setChatInput("");
      setChatting(true);
      setChatLog((prev) => [
        ...prev,
        { role: "user", text: message },
        { role: "assistant", text: "유튜브에 저장을 시작할게요…" },
      ]);
      try {
        const started = await handleSaveYoutube();
        setLastAssistant(
          started
            ? "✅ 유튜브에 저장을 시작했어요. 완료되면 '유튜브에 저장'이 완료로 바뀝니다."
            : "유튜브 저장을 시작하지 못했어요. (연동 취소/오류)",
        );
      } finally {
        setChatting(false);
      }
      return;
    }

    const beforeIds = new Set(selected.items.map((i) => i.video_id));
    setChatInput("");
    setChatting(true);
    setChatLog((prev) => [
      ...prev,
      { role: "user", text: message },
      { role: "assistant", text: "요청을 보내는 중..." },
    ]);
    abortRef.current = new AbortController();
    try {
      await streamPlaylistChat(
        selected.id,
        message,
        {
          onStatus: (s) => setLastAssistant(s),
          onPlaylist: (p) => {
            const afterIds = new Set(p.items.map((i) => i.video_id));
            const added = [...afterIds].filter((id) => !beforeIds.has(id));
            const removed = [...beforeIds].filter((id) => !afterIds.has(id)).length;
            setSelected(p);
            setChangedIds(new Set(added));
            setLastAssistant(
              added.length > 0 || removed > 0
                ? `✅ 영상 ${Math.max(added.length, removed)}개를 바꿨어요. (강조된 항목)`
                : "바꿀 만한 새 영상을 찾지 못했어요.",
            );
          },
        },
        abortRef.current.signal,
      );
    } catch {
      setLastAssistant("수정 중 오류가 발생했어요.");
    } finally {
      setChatting(false);
    }
  };

  // ── 상세 뷰 ──────────────────────────────────────────────────────
  if (selected) {
    const ready = selected.status === "ready";
    return (
      <div className="flex min-h-full flex-col px-4 py-5 sm:px-6 sm:py-6">
        <button
          type="button"
          onClick={() => setSelected(null)}
          className="text-muted-foreground hover:text-foreground mb-4 inline-flex w-fit items-center gap-1.5 text-sm transition-colors"
        >
          <ArrowLeft size={16} />
          재생목록 목록
        </button>

        <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
        <section className="border-border flex-1 rounded-2xl border bg-card px-5 py-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            {editingTitle ? (
              <div className="flex flex-1 items-center gap-2">
                <input
                  autoFocus
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && void handleRename()}
                  className="border-border min-w-0 flex-1 rounded-lg border px-2 py-1 text-base font-semibold"
                />
                <Button size="icon" variant="ghost" onClick={() => void handleRename()}>
                  <Check size={16} />
                </Button>
              </div>
            ) : (
              <div className="flex min-w-0 items-center gap-2">
                <h2 className="truncate text-base font-semibold">
                  {selected.title || "제목 없음"}
                </h2>
                <button
                  type="button"
                  onClick={() => {
                    setTitleDraft(selected.title);
                    setEditingTitle(true);
                  }}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <Pencil size={14} />
                </button>
              </div>
            )}
            <div className="flex shrink-0 items-center gap-2">
              {ready && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleRefreshAll()}
                    disabled={refreshingAll}
                    className="gap-1.5"
                  >
                    <RefreshCw
                      size={14}
                      className={refreshingAll ? "animate-spin" : ""}
                    />
                    전체 새로고침
                  </Button>
                  {selected.youtube_playlist_id ? (
                    <Button size="sm" variant="outline" asChild className="gap-1.5">
                      <a
                        href={`https://www.youtube.com/playlist?list=${selected.youtube_playlist_id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Youtube size={15} />
                        유튜브에서 보기
                      </a>
                    </Button>
                  ) : selected.save_status === "saving" ? (
                    <Button size="sm" disabled className="gap-1.5">
                      <RefreshCw size={15} className="animate-spin" />
                      저장 중…
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => void handleSaveYoutube()}
                      className="gap-1.5"
                    >
                      <Youtube size={15} />
                      {selected.save_status === "failed"
                        ? "다시 저장"
                        : "유튜브에 저장"}
                    </Button>
                  )}
                </>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void handleDelete()}
                className="text-muted-foreground hover:text-destructive gap-1.5"
              >
                <Trash2 size={14} />
                삭제
              </Button>
            </div>
          </div>

          {selected.summary && (
            <p className="text-muted-foreground mb-4 text-sm">{selected.summary}</p>
          )}

          {selected.status === "pending" ? (
            <div className="text-muted-foreground flex flex-col items-center gap-2 py-16 text-center text-sm">
              <RefreshCw size={22} className="animate-spin" />
              재생목록을 만드는 중이에요… (채널 검색·큐레이션)
              <span className="text-xs">
                이 창을 나가도 계속 생성돼요. 잠시 후 자동으로 채워집니다.
              </span>
            </div>
          ) : selected.status === "failed" ? (
            <div className="text-muted-foreground py-16 text-center text-sm">
              생성에 실패했어요. 삭제 후 다시 만들어 주세요.
            </div>
          ) : (
            <ul className="flex flex-col gap-3">
              {selected.items.map((it) => {
              const isChanged = changedIds.has(it.video_id);
              return (
              <li
                key={it.video_id}
                onMouseEnter={
                  isChanged
                    ? () =>
                        setChangedIds((prev) => {
                          if (!prev.has(it.video_id)) return prev;
                          const next = new Set(prev);
                          next.delete(it.video_id);
                          return next;
                        })
                    : undefined
                }
                className={cn(
                  "flex items-start gap-3 rounded-xl border p-2.5 transition-colors",
                  isChanged
                    ? "border-primary bg-primary/5 ring-primary/30 ring-1"
                    : "border-border",
                )}
              >
                <a href={it.url} target="_blank" rel="noreferrer" className="shrink-0">
                  {it.thumbnail_url ? (
                    <img
                      src={it.thumbnail_url}
                      alt=""
                      className="h-[68px] w-[120px] rounded-lg object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="bg-muted h-[68px] w-[120px] rounded-lg" />
                  )}
                </a>
                <div className="min-w-0 flex-1">
                  <a
                    href={it.url}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-primary line-clamp-2 text-sm font-medium"
                  >
                    {it.title}
                  </a>
                  <p className="text-muted-foreground mt-0.5 text-xs">
                    {it.channel}
                    {formatPubDate(it.published_at) &&
                      ` · ${formatPubDate(it.published_at)}`}
                  </p>
                  {it.reason && (
                    <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">
                      {it.reason}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => void handleRefreshItem(it.video_id)}
                  disabled={refreshingId === it.video_id}
                  title="다른 영상으로 교체"
                  className="text-muted-foreground hover:text-foreground shrink-0 p-1"
                >
                  <RefreshCw
                    size={15}
                    className={refreshingId === it.video_id ? "animate-spin" : ""}
                  />
                </button>
              </li>
              );
            })}
            </ul>
          )}
        </section>

        {/* 오른쪽: 채팅 패널 (대화 기록 유지) */}
        <aside className="border-border bg-card flex h-[460px] w-full flex-col rounded-2xl border lg:sticky lg:top-8 lg:h-[calc(100vh-7rem)] lg:w-[340px]">
          <div className="border-border border-b px-4 py-3 text-sm font-semibold">
            채팅으로 다듬기
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3">
            {chatLog.length === 0 ? (
              <p className="text-muted-foreground text-xs leading-relaxed">
                자연어로 재생목록을 수정해요.
                <br />
                예: "경제는 빼고 과학 위주로", "가벼운 걸로 두 개만 바꿔줘"
              </p>
            ) : (
              chatLog.map((m, i) => (
                <div
                  key={i}
                  className={
                    m.role === "user" ? "flex justify-end" : "flex justify-start"
                  }
                >
                  <span
                    className={
                      "max-w-[85%] rounded-2xl px-3 py-1.5 text-xs " +
                      (m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground")
                    }
                  >
                    {m.text}
                  </span>
                </div>
              ))
            )}
          </div>
          <div className="border-border border-t p-3">
            <div className="flex items-center gap-2">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleChat()}
                placeholder={ready ? "수정 요청을 입력하세요" : "생성 완료 후 이용할 수 있어요"}
                disabled={chatting || !ready}
                className="border-border min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm"
              />
              <Button
                size="icon"
                onClick={() => void handleChat()}
                disabled={chatting || !chatInput.trim() || !ready}
              >
                <Send size={15} />
              </Button>
            </div>
          </div>
        </aside>
        </div>
      </div>
    );
  }

  // ── 목록 뷰 ──────────────────────────────────────────────────────
  return (
    <div className="flex min-h-full flex-col px-4 py-5 sm:px-6 sm:py-6">
      <Link
        to={ROUTES.idealManagement}
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex w-fit items-center gap-1.5 text-sm transition-colors"
      >
        <ArrowLeft size={16} />
        이상향 관리
      </Link>

      <div className="mb-5 flex items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <ListVideo size={24} />
          재생목록
        </h1>
        <Button
          size="sm"
          onClick={handleNewClick}
          disabled={creating}
          className="gap-1.5"
        >
          <Plus size={15} className={creating ? "animate-spin" : ""} />
          {creating ? "생성 중…" : "새 재생목록"}
        </Button>
      </div>

      {/* 이상향 선택 팝업 */}
      {showPicker && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setShowPicker(false)}
          />
          <div className="border-border bg-card relative z-10 w-full max-w-md rounded-2xl border p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold">새 재생목록</h3>
              <button
                type="button"
                onClick={() => setShowPicker(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="닫기"
              >
                <X size={18} />
              </button>
            </div>

            {ideals.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                이상향이 없어요. 먼저 이상향을 만들어 주세요.
              </p>
            ) : (
              <div className="flex flex-col gap-5">
                {/* 이상향 선택 (검색 드롭다운) */}
                <div>
                  <p className="mb-2 flex items-center gap-1.5 text-sm font-medium">
                    <Target size={15} className="text-muted-foreground" />
                    이상향
                  </p>
                  <IdealSelect
                    ideals={ideals}
                    value={pickIdealId}
                    onChange={setPickIdealId}
                    labelOf={idealLabel}
                  />
                </div>

                {/* 주기 토글 */}
                <div>
                  <p className="mb-2 text-sm font-medium">주기</p>
                  <div className="flex flex-wrap gap-2">
                    {PERIOD_OPTIONS.map((o) => (
                      <button
                        key={o.value}
                        type="button"
                        onClick={() => setPickPeriod(o.value)}
                        className={pillClass(pickPeriod === o.value)}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                <Button
                  onClick={handleCreateFromPicker}
                  disabled={!pickIdealId || creating}
                  className="mt-1 gap-1.5"
                >
                  <Plus size={15} className={creating ? "animate-spin" : ""} />
                  {creating ? "생성 중…" : "만들기"}
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 필터 + 정렬 */}
      <div className="mb-5 flex items-center gap-2">
        <select
          value={filterIdeal}
          onChange={(e) => onFilterChange(e.target.value)}
          className="border-border bg-card rounded-lg border px-3 py-1.5 text-sm"
        >
          <option value="all">모든 이상향</option>
          {ideals.map((i) => (
            <option key={i.id} value={i.id}>
              {idealLabel(i)}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setSortDesc((v) => !v)}
          className="gap-1.5"
        >
          <ArrowUpDown size={14} />
          {sortDesc ? "최신순" : "오래된순"}
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground py-16 text-center text-sm">
          불러오는 중…
        </p>
      ) : visibleRows.length === 0 ? (
        <div className="border-border text-muted-foreground rounded-2xl border border-dashed bg-card px-6 py-16 text-center text-sm">
          {filterIdeal === "all"
            ? "아직 재생목록이 없어요. 이상향을 선택해 새로 만들어 보세요."
            : "이 이상향의 재생목록이 없어요. "}
          {filterIdeal !== "all" && (
            <>
              <b>새 재생목록</b>을 만들어 보세요.
            </>
          )}
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {visibleRows.map((r) => (
            <li key={r.id} className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void openPlaylist(r.id)}
                className="border-border hover:border-primary/40 flex flex-1 items-center justify-between gap-3 rounded-2xl border bg-card px-4 py-3 text-left transition-colors"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">
                    {r.title || "제목 없음"}
                  </p>
                  <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
                    <Badge variant="outline" className="rounded-full">
                      {r.idealLabel}
                    </Badge>
                    {r.status === "pending" ? (
                      <span className="text-primary inline-flex items-center gap-1">
                        <RefreshCw size={11} className="animate-spin" />
                        생성중
                      </span>
                    ) : r.status === "failed" ? (
                      <span className="text-destructive">생성 실패</span>
                    ) : (
                      <span>영상 {r.item_count}개</span>
                    )}
                    <span>
                      {new Date(r.created_at).toLocaleDateString("ko-KR")}
                    </span>
                  </div>
                </div>
                <ListVideo size={18} className="text-muted-foreground shrink-0" />
              </button>
              <select
                value={r.refresh_period}
                onChange={(e) =>
                  void handleSetPeriod(r.id, e.target.value as PlaylistPeriod)
                }
                onClick={(e) => e.stopPropagation()}
                title="자동 갱신 주기"
                className="border-border bg-card text-muted-foreground focus:border-primary/50 shrink-0 rounded-lg border px-2 py-2 text-xs outline-none"
              >
                {PERIOD_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.value === "none" ? "갱신 없음" : `${o.label} 갱신`}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void handleDeleteRow(r.id)}
                title="삭제"
                className="text-muted-foreground hover:text-destructive shrink-0 rounded-lg p-2 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
