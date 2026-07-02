import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, ChevronRight, RefreshCw, Send } from "lucide-react";

import { fetchMyAnalyses, fetchMyAnalysisSnapshot } from "@/api/analyses";
import type { DbProfileResponse } from "@/api/types/profiler";
import { CompareBars } from "@/components/ideals/CompareBars";
import { RadarCompareChart } from "@/components/ideals/RadarCompareChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TEMPERAMENT_AXES } from "@/lib/analyses/temperament";
import type { AnalysisResultItem } from "@/lib/analyses/types";
import { VALUES_AXES } from "@/lib/analyses/values";
import {
  createIdeal,
  getCurrentAxes,
  getProposals,
  streamChat,
} from "@/api/navigator";
import type {
  AxisScores8,
  AxisScores13,
  ProposalItem,
} from "@/api/types/navigator";
import { AXIS_LABELS, IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";

const AXIS_ORDER = Object.keys(AXIS_LABELS);

function buildAxes(current: AxisScores8, ideal: AxisScores8) {
  return AXIS_ORDER.map((k) => ({
    label: AXIS_LABELS[k],
    current: current[k] ?? 0,
    ideal: ideal[k] ?? 0,
  }));
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

function RefineChat({
  proposal,
  current,
  snapshot,
  onConfirm,
  busy,
}: {
  proposal: ProposalItem;
  current: AxisScores8;
  snapshot: DbProfileResponse | null;
  onConfirm: (
    scores: AxisScores8,
    values: AxisScores13,
    refined: boolean,
  ) => void;
  busy: boolean;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `'${IDEAL_TYPE_LABEL[proposal.ideal_type]}' 이상향을 함께 다듬어볼게요. 어떤 축을 더 올리거나 낮추고 싶으세요?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [working, setWorking] = useState<AxisScores8>(proposal.scores);
  const [working13, setWorking13] = useState<AxisScores13>(
    proposal.values_temperament,
  );
  const [streaming, setStreaming] = useState(false);
  const [refined, setRefined] = useState(false);
  const snapshotPersona = (
    snapshot?.portrait as { persona_label?: string } | null | undefined
  )?.persona_label;

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);
    setStreaming(true);
    try {
      await streamChat(
        {
          message: text,
          working_values: working13,
          ideal_type: proposal.ideal_type,
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
            setWorking(d.behavior);
            setWorking13(d.values_temperament);
            setRefined(true);
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <div className="border-border min-w-0 rounded-2xl border bg-card px-5 py-5 lg:flex-1">
        <div className="mb-3 flex items-center justify-between">
          <Badge variant="outline" className="rounded-full">
            {IDEAL_TYPE_LABEL[proposal.ideal_type]}
          </Badge>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="bg-muted-foreground inline-block h-2 w-4 rounded-full" />
              현재
            </span>
            <span className="flex items-center gap-1.5">
              <span className="bg-primary inline-block h-2 w-4 rounded-full" />
              이상향
            </span>
          </div>
        </div>

        {/* 8축 레이더 + 좌우 설명 */}
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
          <div className="shrink-0 self-center">
            <RadarCompareChart axes={buildAxes(current, working)} size={240} />
          </div>
          <div className="min-w-0 flex-1 space-y-4">
            <div>
              <div className="mb-1 flex items-center gap-2">
                <span className="bg-muted-foreground inline-block h-2 w-2 rounded-full" />
                <p className="text-sm font-semibold">현재 분석</p>
                {snapshotPersona && (
                  <span className="text-muted-foreground text-xs">
                    {snapshotPersona}
                  </span>
                )}
              </div>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {snapshot?.summary_text ||
                  "현재 시청 패턴을 바탕으로 한 행동 성향입니다."}
              </p>
              {snapshot?.tone_of_user && (
                <p className="text-muted-foreground mt-1 text-xs">
                  톤: {snapshot.tone_of_user}
                </p>
              )}
            </div>
            <div>
              <div className="mb-1 flex items-center gap-2">
                <span className="bg-primary inline-block h-2 w-2 rounded-full" />
                <p className="text-sm font-semibold">이상향</p>
                {proposal.persona_label && (
                  <span className="text-primary text-xs font-medium">
                    {proposal.persona_label}
                  </span>
                )}
              </div>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {proposal.reasoning}
              </p>
            </div>
          </div>
        </div>

        {/* 8축 아래: 가치관 10축 · 기질 3축 — 현재 vs 이상향 */}
        {snapshot && (
          <div className="border-border mt-5 space-y-5 border-t pt-5">
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="bg-muted-foreground/50 inline-block h-2 w-4 rounded-full" />
                현재(막대)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="bg-primary inline-block h-3.5 w-[3px] rounded-full" />
                이상향(목표선)
              </span>
            </div>
            <CompareBars
              title="가치관"
              subtitle="0=관심 없음 · 100=강하게 추구"
              axes={VALUES_AXES}
              current={snapshot.scores}
              ideal={working13}
            />
            <CompareBars
              title="기질"
              subtitle="시청에서 읽히는 성향 · 0=약함 · 100=강함"
              axes={TEMPERAMENT_AXES}
              current={snapshot.scores}
              ideal={working13}
            />
          </div>
        )}
      </div>

        <div className="border-border flex flex-col rounded-2xl border bg-card lg:sticky lg:top-4 lg:w-[400px] lg:shrink-0">
        <div className="flex max-h-[320px] min-h-[180px] flex-col gap-3 overflow-y-auto px-5 py-4 lg:max-h-[60vh]">
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
        <div className="border-border flex items-center gap-2 border-t px-3 py-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void send();
            }}
            placeholder="조정하고 싶은 내용을 입력하세요"
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

      <div className="flex justify-end">
        <Button
          onClick={() => onConfirm(working, working13, refined)}
          disabled={busy}
          className="gap-1.5"
        >
          <Check size={16} />
          이 이상향으로 확정하기
        </Button>
      </div>
    </div>
  );
}

function ShowProposals({
  analysisId,
  onBack,
}: {
  analysisId: string;
  onBack: () => void;
}) {
  const navigate = useNavigate();
  const [proposals, setProposals] = useState<ProposalItem[]>([]);
  const [current, setCurrent] = useState<AxisScores8>({});
  const [snapshot, setSnapshot] = useState<DbProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const regenerate = async () => {
    setRegenerating(true);
    setError(null);
    try {
      const prop = await getProposals(analysisId || undefined, true);
      setProposals(prop.proposals);
      setSelected(prop.proposals[0]?.ideal_type ?? null);
    } catch {
      setError("추천을 다시 생성하지 못했습니다.");
    } finally {
      setRegenerating(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [prop, snap] = await Promise.all([
          getProposals(analysisId || undefined),
          analysisId
            ? fetchMyAnalysisSnapshot(analysisId).catch(() => null)
            : Promise.resolve(null),
        ]);
        if (cancelled) return;
        setProposals(prop.proposals);
        setSnapshot(snap);
        // 현재 8축: 스냅샷에서 추출, 없으면 최신 프로필로 폴백
        if (snap) {
          setCurrent(
            Object.fromEntries(
              AXIS_ORDER.map((k) => [k, snap.scores[k] ?? 0]),
            ),
          );
        } else {
          setCurrent(await getCurrentAxes().catch(() => ({}) as AxisScores8));
        }
        setSelected(prop.proposals[0]?.ideal_type ?? null);
      } catch {
        if (!cancelled) setError("제안을 불러오지 못했습니다. (프로필이 필요합니다)");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  const confirmCreate = async (
    ideal_type: ProposalItem["ideal_type"],
    scores: AxisScores8,
    reasoning: string,
    persona_label: string,
    values_temperament?: AxisScores13,
  ) => {
    setBusy(true);
    try {
      const created = await createIdeal({
        ideal_type,
        scores,
        values_temperament,
        persona_label: persona_label || undefined,
        reasoning,
        source_profile_history_id: analysisId || undefined,
      });
      navigate(ROUTES.idealDetail(created.id));
    } catch {
      setError("이상향 저장에 실패했습니다.");
      setBusy(false);
    }
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

  const selectedProposal =
    proposals.find((p) => p.ideal_type === selected) ?? proposals[0] ?? null;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">추천 이상향 3안</h2>
          <p className="text-muted-foreground mt-1 text-xs">
            카드를 골라 아래에서 대화로 다듬어 보세요. (현재 파랑 · 이상향 인디고)
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void regenerate()}
          disabled={regenerating}
          className="shrink-0 gap-1.5"
        >
          <RefreshCw size={14} className={regenerating ? "animate-spin" : ""} />
          다시 추천
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {proposals.map((p) => {
          const active = selectedProposal?.ideal_type === p.ideal_type;
          return (
            <button
              key={p.ideal_type}
              type="button"
              onClick={() => setSelected(p.ideal_type)}
              className={cn(
                "flex h-full flex-col rounded-2xl border bg-card px-4 py-4 text-left transition-colors",
                active
                  ? "border-primary bg-primary/5 ring-primary/30 ring-1"
                  : "border-border hover:border-primary/40",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <Badge variant="outline" className="rounded-full">
                  {IDEAL_TYPE_LABEL[p.ideal_type]}
                </Badge>
                {active && <Check size={16} className="text-primary shrink-0" />}
              </div>
              {p.persona_label && (
                <p className="mt-2 text-sm font-semibold">{p.persona_label}</p>
              )}
              <p className="text-muted-foreground mt-1 line-clamp-3 text-xs leading-relaxed">
                {p.reasoning}
              </p>
            </button>
          );
        })}
      </div>

      {selectedProposal && (
        <RefineChat
          key={selectedProposal.ideal_type}
          proposal={selectedProposal}
          current={current}
          snapshot={snapshot}
          busy={busy}
          onConfirm={(scores, values, refined) =>
            void confirmCreate(
              refined ? "CUSTOM" : selectedProposal.ideal_type,
              scores,
              selectedProposal.reasoning,
              refined ? "" : selectedProposal.persona_label,
              values,
            )
          }
        />
      )}

      <div className="flex justify-start">
        <Button variant="outline" onClick={onBack} className="gap-1.5">
          <ArrowLeft size={16} />
          분석 다시 선택
        </Button>
      </div>
    </div>
  );
}

export function IdealSetupPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [analyses, setAnalyses] = useState<AnalysisResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState("");

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
        setAnalysisId(completed[0]?.id ?? "");
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
    <div
      className={cn(
        "flex min-h-full flex-col px-4 py-5 sm:px-6 sm:py-6",
      )}
    >
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
        <ShowProposals analysisId={analysisId} onBack={() => setStep(1)} />
      )}
    </div>
  );
}
