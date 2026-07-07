import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Check, ChevronRight, Send } from "lucide-react";

import { fetchMyAnalyses, fetchMyAnalysisSnapshot } from "@/api/analyses";
import type { DbProfileResponse } from "@/api/types/profiler";
import { InterestPie, buildInterestLegend } from "@/components/analyses/interest-pie";
import { RadarCompareChart } from "@/components/ideals/RadarCompareChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AnalysisResultItem } from "@/lib/analyses/types";
import {
  createIdeal,
  getChatHistory,
  getProposals,
  streamChat,
} from "@/api/navigator";
import type {
  AxisScores8,
  AxisScores13,
  CompleteEvent,
  IdealType,
  ProposalItem,
} from "@/api/types/navigator";
import { IDEAL_TYPE_DESC, IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";

/** 추천 3안이 준비될 때까지 폴링한다 (백엔드가 백그라운드로 생성). */
async function pollProposals(
  analysisId: string | undefined,
  opts: { refresh?: boolean; shouldCancel: () => boolean },
) {
  let res = await getProposals(analysisId, opts.refresh ?? false);
  while (res.status === "pending" && !opts.shouldCancel()) {
    await new Promise((r) => setTimeout(r, 3000));
    if (opts.shouldCancel()) break;
    res = await getProposals(analysisId);
  }
  return res;
}

function StepHeader({ step }: { step: 1 | 2 }) {
  const steps = [
    { n: 1, label: "분석 선택" },
    { n: 2, label: "이상향 추천" },
  ];
  return (
    <div className="mb-6 flex items-center gap-2">
      {steps.map((s, i) => (
        <div key={s.n} className="flex items-center gap-2">
          <span
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold",
              step >= s.n
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground",
            )}
          >
            {s.n}
          </span>
          <span
            className={cn(
              "text-sm",
              step >= s.n ? "font-medium" : "text-muted-foreground",
            )}
          >
            {s.label}
          </span>
          {i === 0 && (
            <ChevronRight size={16} className="text-muted-foreground" />
          )}
        </div>
      ))}
    </div>
  );
}

function SelectAnalysis({
  analyses,
  loading,
  error,
  selectedId,
  onSelect,
  onNext,
}: {
  analyses: AnalysisResultItem[];
  loading: boolean;
  error: string | null;
  selectedId: string;
  onSelect: (id: string) => void;
  onNext: () => void;
}) {
  return (
    <>
      <div className="border-border mb-5 rounded-2xl border bg-card px-5 py-5">
        <p className="text-sm font-semibold">
          이 분석을 기반으로 이상향을 설정할까요?
        </p>
        <p className="text-muted-foreground mt-1 text-xs">
          가장 최근 분석이 기본 선택돼 있어요.
        </p>

        {loading ? (
          <p className="text-muted-foreground mt-4 text-sm">
            분석 목록 불러오는 중…
          </p>
        ) : error ? (
          <p className="text-destructive mt-4 text-sm">{error}</p>
        ) : analyses.length === 0 ? (
          <div className="mt-4 flex flex-col items-start gap-3">
            <p className="text-muted-foreground text-sm">
              완료된 분석이 없습니다. 먼저 시청 기록을 업로드해 분석을 완료해 주세요.
            </p>
            <Button asChild variant="outline" size="sm">
              <Link to={ROUTES.upload}>분석하러 가기</Link>
            </Button>
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-2">
            {analyses.map((a, i) => {
              const selected = a.id === selectedId;
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => onSelect(a.id)}
                  className={cn(
                    "flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors",
                    selected
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/40",
                  )}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">
                        {a.title}
                      </span>
                      {i === 0 && (
                        <Badge variant="indigo" className="rounded-full">
                          최신
                        </Badge>
                      )}
                    </div>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                      {a.date}
                    </p>
                  </div>
                  {selected && (
                    <Check size={18} className="text-primary shrink-0" />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
      <div className="flex justify-end">
        <Button
          onClick={onNext}
          disabled={loading || !selectedId}
          className="gap-1.5"
        >
          다음
          <ChevronRight size={16} />
        </Button>
      </div>
    </>
  );
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const GREETING: ChatMessage = {
  role: "assistant",
  content:
    "이상향을 함께 만들어볼게요. 요즘 어떤 콘텐츠가 끌리는지, 뭘 더 보고 싶은지 편하게 말씀해 주세요. 마음에 드는 카드를 골라 시작해도 좋아요.",
};

/** 설계 대화 세션 id.
 * - resume=true(배너 '이어서 분석하기')  → 그 스냅샷의 기존 세션을 재사용(대화 복원).
 * - resume=false(새로 설계)              → 새 세션을 만들어 저장(옛 대화 안 남음).
 *   (새로 만든 세션도 저장해두므로, 도중에 나갔다 배너로 돌아오면 이어집니다.)
 */
function resolveSessionId(analysisId: string, resume: boolean): string {
  const key = `nav_session:${analysisId || "latest"}`;
  try {
    if (resume) {
      const existing = localStorage.getItem(key);
      if (existing) return existing;
    }
    const id = crypto.randomUUID();
    localStorage.setItem(key, id);
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

/** 대화로 만든 이상향(성향·도메인·8·13)을 세션 단위로 보관해 이어서 설계 시 복원. */
interface LiveIdeal {
  disposition: Record<string, number> | null;
  interest: Record<string, number> | null;
  behavior: AxisScores8 | null;
  values: AxisScores13 | null;
  keywords?: string[];
}
function saveLiveIdeal(sessionId: string, v: LiveIdeal): void {
  try {
    localStorage.setItem(`nav_ideal:${sessionId}`, JSON.stringify(v));
  } catch {
    /* 무시 */
  }
}
function loadLiveIdeal(sessionId: string): LiveIdeal | null {
  try {
    const raw = localStorage.getItem(`nav_ideal:${sessionId}`);
    return raw ? (JSON.parse(raw) as LiveIdeal) : null;
  } catch {
    return null;
  }
}

function snapshotPersonaOf(snapshot: DbProfileResponse | null): string {
  return (
    (snapshot?.portrait as { persona_label?: string } | null | undefined)
      ?.persona_label ?? ""
  );
}

/** 접힌 카드(3안 중 하나) — 클릭하면 펼침 + 선택. */
function ProposalCard({
  proposal,
  onSelect,
}: {
  proposal: ProposalItem;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="border-border hover:border-primary/40 flex flex-1 flex-col rounded-2xl border bg-card px-4 py-4 text-left transition-colors"
    >
      <Badge variant="outline" className="w-fit rounded-full">
        {IDEAL_TYPE_LABEL[proposal.ideal_type]}
      </Badge>
      {proposal.persona_label && (
        <p className="mt-2 text-sm font-semibold">{proposal.persona_label}</p>
      )}
      <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
        {IDEAL_TYPE_DESC[proposal.ideal_type]}
      </p>
    </button>
  );
}

/** 펼친 카드 — 행 전체를 덮고 상세 표시, 뒤로 누르면 3개로 복귀. */
function ExpandedProposal({
  proposal,
  onBack,
}: {
  proposal: ProposalItem;
  onBack: () => void;
}) {
  return (
    <div className="border-primary bg-primary/5 ring-primary/20 flex-1 rounded-2xl border px-5 py-5 ring-1">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex flex-col items-start gap-1.5">
          <Badge variant="outline" className="rounded-full">
            {IDEAL_TYPE_LABEL[proposal.ideal_type]}
          </Badge>
          {proposal.persona_label && (
            <span className="text-primary text-sm font-semibold">
              {proposal.persona_label}
            </span>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-1.5">
          <ArrowLeft size={16} />
          뒤로
        </Button>
      </div>
      <div>
        <div className="mb-1 flex items-center gap-2">
          <span className="bg-primary inline-block h-2 w-2 rounded-full" />
          <p className="text-sm font-semibold">이상향</p>
        </div>
        <p className="text-muted-foreground text-sm leading-relaxed">
          {proposal.reasoning}
        </p>
      </div>
    </div>
  );
}

/** 좌측 패널 — 현재 생성 예상 이상향: 성향 6각 + 관심 도메인(현재/이상향). */
function IdealCharts({
  dispRadar,
  curPie,
  idealPie,
}: {
  dispRadar: { label: string; current: number; ideal: number }[];
  curPie: { axis: string; value: number }[];
  idealPie: { axis: string; value: number }[] | null;
}) {
  return (
    <div className="border-border h-full space-y-4 rounded-2xl border bg-card px-4 py-4">
      {/* 성향 6각 */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <p className="text-sm font-semibold">성향</p>
          <div className="text-muted-foreground flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="bg-muted-foreground inline-block h-2 w-4 rounded-full" />
              현재
            </span>
            {idealPie && (
              <span className="flex items-center gap-1.5">
                <span className="bg-primary inline-block h-2 w-4 rounded-full" />
                이상향
              </span>
            )}
          </div>
        </div>
        {dispRadar.length > 0 ? (
          <div className="flex justify-center">
            <RadarCompareChart axes={dispRadar} size={250} labelMargin={38} />
          </div>
        ) : (
          <p className="text-muted-foreground py-6 text-center text-sm">
            성향 데이터가 없습니다. "다시 추천"으로 새로 생성해 보세요.
          </p>
        )}
      </div>

      {/* 관심 도메인 — 좌측 공유 범례 + 도넛(현재/이상향) */}
      <div className="border-border border-t pt-4">
        <p className="mb-2 text-sm font-semibold">관심 도메인</p>
        <div className="flex items-start gap-3">
          <ul className="border-border flex w-24 shrink-0 flex-col gap-1 rounded-xl border p-2.5">
            {[...buildInterestLegend(curPie)]
              .sort((a, b) => b.value - a.value)
              .map((l) => (
                <li
                  key={l.axis}
                  className="flex items-center gap-1.5 text-[10px] leading-tight"
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ background: l.color }}
                  />
                  <span className="flex-1 whitespace-nowrap">{l.axis}</span>
                </li>
              ))}
          </ul>
          <div className="flex min-w-0 flex-1 items-start justify-center gap-3">
            <div className="min-w-0 flex-1">
              {idealPie && (
                <p className="text-muted-foreground mb-1 text-center text-xs">
                  현재
                </p>
              )}
              <InterestPie
                data={curPie}
                size={idealPie ? 150 : 200}
                showLegend={false}
                innerRadius="52%"
                outerRadius="94%"
              />
            </div>
            {idealPie && (
              <div className="min-w-0 flex-1">
                <p className="text-primary mb-1 text-center text-xs">이상향</p>
                <InterestPie
                  data={idealPie}
                  size={150}
                  showLegend={false}
                  innerRadius="52%"
                  outerRadius="94%"
                />
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}

function ShowProposals({
  analysisId,
  resume,
  onBack,
}: {
  analysisId: string;
  resume: boolean;
  onBack: () => void;
}) {
  const navigate = useNavigate();
  const [proposals, setProposals] = useState<ProposalItem[]>([]);
  const [snapshot, setSnapshot] = useState<DbProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<IdealType | null>(null);
  const [busy, setBusy] = useState(false);

  // 챗 상태 (선택 없이도 대화 가능) — 세션은 스냅샷 단위로 고정해 대화가 유지됨
  const [sessionId] = useState(() => resolveSessionId(analysisId, resume));
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  // 대화로 실시간 갱신되는 이상향(성향·도메인·8·13) + 완성 결과
  const [liveDisp, setLiveDisp] = useState<Record<string, number> | null>(null);
  const [liveInt, setLiveInt] = useState<Record<string, number> | null>(null);
  const [liveBehavior, setLiveBehavior] = useState<AxisScores8 | null>(null);
  const [liveValues, setLiveValues] = useState<AxisScores13 | null>(null);
  const [liveKeywords, setLiveKeywords] = useState<string[]>([]);
  const [finalIdeal, setFinalIdeal] = useState<CompleteEvent | null>(null);
  // 대화 마무리 후 '넘어갈지/더 대화할지' 확인 팝업
  const [pendingFinalize, setPendingFinalize] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  // 새 메시지/토큰마다 대화창을 맨 아래로 자동 스크롤
  useEffect(() => {
    const el = chatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // 마운트 시 이전 설계 대화 + 대화로 만든 이상향(차트) 복원 (이어서 설계하기)
  useEffect(() => {
    let cancelled = false;
    const savedIdeal = loadLiveIdeal(sessionId);
    if (savedIdeal) {
      setLiveDisp(savedIdeal.disposition);
      setLiveInt(savedIdeal.interest);
      setLiveBehavior(savedIdeal.behavior);
      setLiveValues(savedIdeal.values);
      setLiveKeywords(savedIdeal.keywords ?? []);
    }
    void getChatHistory(sessionId)
      .then((hist) => {
        if (cancelled || hist.length === 0) return;
        setMessages([
          GREETING,
          ...hist
            .filter((h) => h.role === "user" || h.role === "assistant")
            .map((h) => ({
              role: h.role as ChatMessage["role"],
              content: h.content,
            })),
        ]);
      })
      .catch(() => {
        /* 이력 없음/오류 무시 — 인사말만 */
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const selectedProposal =
    proposals.find((p) => p.ideal_type === selected) ?? null;

  const dispTargetMap = (p: ProposalItem) =>
    Object.fromEntries(p.disposition.map((x) => [x.key, x.target]));
  const intTargetMap = (p: ProposalItem) =>
    Object.fromEntries(p.interest.map((x) => [x.domain, x.target]));

  // 카드를 펼쳤다 접어도 대화로 만든 이상향(live/final)은 유지한다.
  // 차트 이상향 우선순위는 liveDisp ?? 선택 카드 목표(아래 렌더 참고).

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const snapPromise = analysisId
          ? fetchMyAnalysisSnapshot(analysisId).catch(() => null)
          : Promise.resolve(null);
        const prop = await pollProposals(analysisId || undefined, {
          shouldCancel: () => cancelled,
        });
        const snap = await snapPromise;
        if (cancelled) return;
        if (prop.status === "failed") {
          setError("추천 생성에 실패했어요. 다시 시도해 주세요.");
        } else {
          setProposals(prop.proposals);
        }
        setSnapshot(snap);
      } catch {
        if (!cancelled)
          setError("제안을 불러오지 못했습니다. (프로필이 필요합니다)");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  const saveIdealAndGo = async (body: Parameters<typeof createIdeal>[0]) => {
    setBusy(true);
    try {
      const created = await createIdeal(body);
      navigate(ROUTES.idealDetail(created.id));
    } catch {
      setError("이상향 저장에 실패했습니다.");
      setBusy(false);
    }
  };

  const send = async (opts?: { force?: boolean }) => {
    const force = opts?.force ?? false;
    const text = input.trim();
    if (streaming || (!force && !text)) return;
    if (text) {
      setInput("");
      setMessages((m) => [
        ...m,
        { role: "user", content: text },
        { role: "assistant", content: "" },
      ]);
    } else {
      setMessages((m) => [...m, { role: "assistant", content: "" }]);
    }
    setStreaming(true);
    try {
      await streamChat(
        {
          message: text,
          session_id: sessionId,
          working_values:
            liveValues ?? selectedProposal?.values_temperament ?? undefined,
          working_disposition:
            liveDisp ??
            (selectedProposal ? dispTargetMap(selectedProposal) : undefined),
          working_interest:
            liveInt ??
            (selectedProposal ? intTargetMap(selectedProposal) : undefined),
          ideal_type: selected ?? undefined,
          force_finalize: force,
        },
        {
          onToken: (c) =>
            setMessages((m) => {
              const upd = [...m];
              const last = upd[upd.length - 1];
              upd[upd.length - 1] = { ...last, content: last.content + c };
              return upd;
            }),
          onIdeal: (d) => {
            setLiveDisp(d.disposition);
            setLiveInt(d.interest);
            setLiveBehavior(d.behavior);
            setLiveValues(d.values_temperament);
            setLiveKeywords(d.keywords ?? []);
            saveLiveIdeal(sessionId, {
              disposition: d.disposition,
              interest: d.interest,
              behavior: d.behavior,
              values: d.values_temperament,
              keywords: d.keywords ?? [],
            });
          },
          onComplete: (d) => {
            setFinalIdeal(d);
            setLiveDisp(d.disposition);
            setLiveInt(d.interest);
            setLiveBehavior(d.behavior);
            setLiveValues(d.values_temperament);
            setLiveKeywords(d.keywords ?? []);
            saveLiveIdeal(sessionId, {
              disposition: d.disposition,
              interest: d.interest,
              behavior: d.behavior,
              values: d.values_temperament,
              keywords: d.keywords ?? [],
            });
            // 바로 넘어가지 말고 확인 팝업 — 마지막 멘트를 읽고 넘어갈지/더 대화할지 선택
            setPendingFinalize(true);
          },
        },
      );
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "오류가 발생했습니다." },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  const hasChatIdeal = liveDisp !== null || finalIdeal !== null;

  const confirmCreate = () => {
    if (!selectedProposal && !hasChatIdeal) return;
    // 카드가 선택돼 있으면 그 카드를, 아니면 대화로 만든 이상향(CUSTOM)을 저장
    const body = selectedProposal
      ? {
          ideal_type: selectedProposal.ideal_type,
          scores: selectedProposal.scores,
          values_temperament: selectedProposal.values_temperament,
          target_disposition: dispTargetMap(selectedProposal),
          target_interest: intTargetMap(selectedProposal),
          persona_label: selectedProposal.persona_label || undefined,
          reasoning: selectedProposal.reasoning,
          source_profile_history_id: analysisId || undefined,
        }
      : {
          ideal_type: "CUSTOM" as const,
          scores: liveBehavior ?? {},
          values_temperament: liveValues ?? undefined,
          target_disposition: liveDisp ?? {},
          target_interest: liveInt ?? {},
          persona_label: finalIdeal?.persona_label || undefined,
          reasoning: finalIdeal?.reasoning || "",
          taste_keywords: liveKeywords,
          source_profile_history_id: analysisId || undefined,
        };
    void saveIdealAndGo(body);
  };

  if (loading) {
    return <p className="text-muted-foreground text-sm">제안 생성 중…</p>;
  }
  if (error) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-destructive text-sm">{error}</p>
        <Button variant="outline" onClick={onBack} className="w-fit gap-1.5">
          <ArrowLeft size={16} />
          분석 다시 선택
        </Button>
      </div>
    );
  }

  // 차트 데이터: 현재는 아무 제안의 pair(current 동일)에서.
  // 이상향은 대화로 갱신된 값(live) 우선, 없으면 선택 제안의 target.
  const baseDisp = proposals[0]?.disposition ?? [];
  const baseInt = proposals[0]?.interest ?? [];
  // 카드 선택 시엔 그 카드 목표를 보여주고, 아니면 대화로 만든 이상향(유지됨).
  const idealDispMap = selectedProposal
    ? dispTargetMap(selectedProposal)
    : liveDisp;
  const idealIntMap = selectedProposal
    ? intTargetMap(selectedProposal)
    : liveInt;
  const dispRadar = baseDisp.map((p) => ({
    label: p.label_ko,
    current: p.current,
    ideal: idealDispMap ? (idealDispMap[p.key] ?? p.current) : p.current,
  }));
  const curPie = baseInt.map((p) => ({ axis: p.domain, value: p.current }));
  const idealPie = idealIntMap
    ? baseInt.map((p) => ({ axis: p.domain, value: idealIntMap[p.domain] ?? 0 }))
    : null;
  const currentPersona = snapshot ? snapshotPersonaOf(snapshot) : null;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <h2 className="text-base font-semibold">추천 이상향 3안</h2>
            {currentPersona && (
              <span className="text-muted-foreground text-xs">
                현재 분석 · <span className="font-medium">{currentPersona}</span>
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-1 text-xs">
            카드를 고르면 상세와 예상 이상향 차트가 보여요. 선택 없이 대화만 해도
            됩니다.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onBack}
            className="gap-1.5"
          >
            <ArrowLeft size={16} />
            분석 다시 선택
          </Button>
          <Button
            size="sm"
            onClick={() => void confirmCreate()}
            disabled={busy || (!selectedProposal && !hasChatIdeal)}
            className="gap-1.5"
          >
            <Check size={16} />
            이 이상향으로 확정하기
          </Button>
        </div>
      </div>

      {/* 좌: 추천 3안 + 성향/관심 차트  ·  우: 채팅. 3열 높이 고정(동일) — 채팅으로 안 늘어남 */}
      <div className="flex flex-col gap-4 lg:h-[calc(100vh-16rem)] lg:flex-row">
        {/* 1열: 이상향 3안 (세로) — 카드 or 펼침 */}
        <div className="flex flex-col gap-3 lg:w-[300px] lg:shrink-0">
          {selectedProposal ? (
            <ExpandedProposal
              proposal={selectedProposal}
              onBack={() => setSelected(null)}
            />
          ) : (
            proposals.map((p) => (
              <ProposalCard
                key={p.ideal_type}
                proposal={p}
                onSelect={() => setSelected(p.ideal_type)}
              />
            ))
          )}
        </div>

        {/* 2열: 성향 + 관심 도메인 */}
        <div className="min-w-0 flex-1">
          <IdealCharts
            dispRadar={dispRadar}
            curPie={curPie}
            idealPie={idealPie}
          />
        </div>

        {/* 우 컬럼 — 채팅 (좌 컬럼 높이에 맞춰 세로로 채움) */}
        <div className="border-border flex min-h-[440px] flex-col overflow-hidden rounded-2xl border bg-card lg:max-h-[calc(100vh-13rem)] lg:w-[380px] lg:shrink-0">
          <div
            ref={chatScrollRef}
            className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-5 py-4"
          >
            {messages.map((m, i) => (
              <div
                key={i}
                className={cn(
                  "flex",
                  m.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap",
                    m.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-foreground",
                  )}
                >
                  {m.content || (streaming ? "…" : "")}
                </div>
              </div>
            ))}
          </div>
          <div className="border-border flex items-center gap-2 border-t px-3 pt-3 pb-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void send();
              }}
              placeholder="어떤 콘텐츠가 끌리는지 편하게 말해보세요"
              className="flex-1"
            />
            <Button
              size="icon"
              onClick={() => void send()}
              disabled={streaming}
              aria-label="전송"
            >
              <Send size={16} />
            </Button>
          </div>
        </div>
      </div>

      {pendingFinalize && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => !busy && setPendingFinalize(false)}
          />
          <div className="border-border bg-card relative z-10 w-full max-w-sm rounded-2xl border p-5 shadow-xl">
            <h3 className="text-base font-semibold">이상향을 완성했어요</h3>
            {finalIdeal?.persona_label && (
              <p className="text-primary mt-1 text-sm font-medium">
                {finalIdeal.persona_label}
              </p>
            )}
            <p className="text-muted-foreground mt-2 text-sm">
              이 이상향으로 넘어갈까요? 더 이야기하고 싶으면 계속 대화해도 돼요.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPendingFinalize(false)}
                disabled={busy}
              >
                더 대화하기
              </Button>
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => confirmCreate()}
                disabled={busy}
              >
                <Check size={15} />
                이 이상향으로 확정
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function IdealSetupPage() {
  const [searchParams] = useSearchParams();
  // 이어서 분석하기: ?analysis=<스냅샷> 이면 바로 이상향 추천(step 2)으로
  const resumeAnalysis = searchParams.get("analysis");
  const [step, setStep] = useState<1 | 2>(resumeAnalysis ? 2 : 1);
  const [analyses, setAnalyses] = useState<AnalysisResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState(resumeAnalysis ?? "");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await fetchMyAnalyses();
        if (cancelled) return;
        const completed = list.filter((a) => a.status === "completed");
        setAnalyses(completed);
        if (!resumeAnalysis) setAnalysisId(completed[0]?.id ?? "");
      } catch {
        if (!cancelled) setError("분석 목록을 불러오지 못했습니다.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={cn("flex min-h-full flex-col px-4 py-5 sm:px-6 sm:py-6")}>
      <Link
        to={ROUTES.idealManagement}
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex w-fit items-center gap-1.5 text-sm transition-colors"
      >
        <ArrowLeft size={16} />
        이상향 관리
      </Link>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">이상향 설정</h1>
      <StepHeader step={step} />
      {step === 1 ? (
        <SelectAnalysis
          analyses={analyses}
          loading={loading}
          error={error}
          selectedId={analysisId}
          onSelect={setAnalysisId}
          onNext={() => setStep(2)}
        />
      ) : (
        <ShowProposals
          analysisId={analysisId}
          resume={Boolean(resumeAnalysis)}
          onBack={() => setStep(1)}
        />
      )}
    </div>
  );
}
