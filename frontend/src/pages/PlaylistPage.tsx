import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpDown,
  Check,
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
  streamPlaylistChat,
} from "@/api/navigator";
import { connectYoutube } from "@/lib/youtube-connect";
import type {
  IdealResponse,
  PlaylistResponse,
  PlaylistSummary,
} from "@/api/types/navigator";
import { IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { ROUTES } from "@/routes";

type Row = PlaylistSummary & { idealId: string; idealLabel: string };

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

  // 상세
  const [selected, setSelected] = useState<PlaylistResponse | null>(null);
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
    setSelected(await getPlaylist(playlistId));
  };

  const createFor = async (idealId: string) => {
    setShowPicker(false);
    setCreating(true);
    try {
      const created = await createPlaylist(idealId);
      const i = ideals.find((x) => x.id === idealId);
      setRows((prev) => [
        {
          id: created.id,
          title: created.title,
          item_count: created.items.length,
          status: created.status,
          save_status: created.save_status,
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

  const handleNewClick = () => {
    // 특정 이상향이 필터에 선택돼 있으면 바로, "모든 이상향"이면 항상 고르게
    if (filterIdeal !== "all") return void createFor(filterIdeal);
    setShowPicker((v) => !v);
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

  const handleSaveYoutube = async () => {
    if (!selected) return;
    const id = selected.id;
    try {
      let res = await savePlaylistToYoutube(id);
      if (res.needs_reconsent) {
        try {
          await connectYoutube(); // youtube 스코프 동의 팝업
        } catch {
          return; // 동의 취소
        }
        res = await savePlaylistToYoutube(id);
        if (res.needs_reconsent) return;
      }
      markSaving(id); // 폴링이 완료를 채움
    } catch {
      window.alert("저장을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
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
            const changed = [...beforeIds].filter((id) => !afterIds.has(id)).length;
            setSelected(p);
            setLastAssistant(
              changed > 0
                ? `✅ 영상 ${changed}개를 바꿨어요.`
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
              {selected.items.map((it) => (
              <li
                key={it.video_id}
                className="border-border flex items-start gap-3 rounded-xl border p-2.5"
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
                  <p className="text-muted-foreground mt-0.5 text-xs">{it.channel}</p>
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
            ))}
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
          <div className="border-border bg-card relative z-10 w-full max-w-sm rounded-2xl border p-5 shadow-xl">
            <div className="mb-1 flex items-center justify-between">
              <h3 className="text-base font-semibold">이상향 선택</h3>
              <button
                type="button"
                onClick={() => setShowPicker(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="닫기"
              >
                <X size={18} />
              </button>
            </div>
            <p className="text-muted-foreground mb-4 text-sm">
              어느 이상향으로 재생목록을 만들까요?
            </p>
            {ideals.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                이상향이 없어요. 먼저 이상향을 만들어 주세요.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {ideals.map((i) => (
                  <li key={i.id}>
                    <button
                      type="button"
                      onClick={() => void createFor(i.id)}
                      className="border-border hover:border-primary/40 hover:bg-secondary flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors"
                    >
                      <Target size={18} className="text-muted-foreground shrink-0" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">
                          {idealLabel(i)}
                        </span>
                        <span className="text-muted-foreground block truncate text-xs">
                          {i.reasoning || IDEAL_TYPE_LABEL[i.ideal_type]}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
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
