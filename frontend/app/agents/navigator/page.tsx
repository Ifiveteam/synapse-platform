"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { MOCK_PROFILER_DATA } from "@/lib/navigator-mock";
import type { IdealType, IdealRadarChart, Guide, Quest } from "@/lib/navigator-types";
import { NavigatorRadarChart } from "@/components/navigator/radar-chart";
import { LayerBGauge } from "@/components/navigator/layer-b-gauge";
import { AXIS_LABELS } from "@/lib/navigator-types";
import { IdealSelector } from "@/components/navigator/ideal-selector";
import { GuideRoadmap, QuestCard } from "@/components/navigator/quest-card";
import { ROUTES } from "@/lib/routes";
import {
  designIdeal,
  confirmIdeal,
} from "@/lib/navigator-api";
import type { IdealDesignResponse } from "@/lib/navigator-api";

// ── 탭 정의 ──────────────────────────────────

type Tab = "profile" | "ideal" | "guide";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "profile", label: "현재 프로필",    icon: "📊" },
  { id: "ideal",   label: "이상향 선택",    icon: "🎯" },
  { id: "guide",   label: "가이드 & 퀘스트", icon: "🗺️" },
];

// ── Profiler 데이터 (Profiler Agent 연동 전 임시) ──
// TODO: Profiler Agent 완성 후 실제 API로 교체
const PROFILER_DATA = MOCK_PROFILER_DATA;

// ── dominant/weak 계산 ──────────────────────

function computeDominantWeak(layerA: Record<string, number>, threshold = 15) {
  const entries = Object.entries(layerA).filter(([k]) => k !== "user_id");
  const mean    = entries.reduce((s, [, v]) => s + v, 0) / entries.length;
  const sorted  = [...entries].sort((a, b) => b[1] - a[1]);
  const dominant = sorted.slice(0, 2).filter(([, v]) => v >= mean + threshold / 2).map(([k]) => k);
  const weakSorted = [...entries].sort((a, b) => a[1] - b[1]);
  const weak    = weakSorted.slice(0, 2).filter(([, v]) => v <= mean - threshold / 2).map(([k]) => k);
  return { dominant, weak };
}

// ── 프로필 섹션 ──────────────────────────────

function ProfileSection() {
  const data = PROFILER_DATA;
  const { dominant, weak } = computeDominantWeak(data.layer_a as unknown as Record<string, number>);

  const dominantLabels = dominant.map((a) => AXIS_LABELS[a as keyof typeof AXIS_LABELS] ?? a).join(", ");
  const weakLabels     = weak.map((a) => AXIS_LABELS[a as keyof typeof AXIS_LABELS] ?? a).join(", ");

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-1 text-sm font-semibold text-gray-700">Layer A — Profiler 8각</h3>
        <p className="mb-4 text-[11px] text-gray-400">YouTube 콘텐츠 소비 행동 측정값 (Profiler v1.1)</p>
        <NavigatorRadarChart current={data.layer_a} size={340} />
      </div>

      <div className="flex flex-col gap-4">
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">프로필 분석</h4>
          <div className="space-y-1.5">
            <div>
              <span className="text-[10px] font-semibold text-rose-500">주 성향축 ▲</span>
              <p className="text-xs text-gray-600">{dominantLabels || "—"}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold text-blue-500">공백축 ▽</span>
              <p className="text-xs text-gray-600">{weakLabels || "—"}</p>
            </div>
          </div>
          <div className="mt-3 space-y-2 border-t border-gray-100 pt-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">취향 다양성</span>
              <span className={`font-semibold ${data.layer_b.taste_diversity_index < 50 ? "text-amber-600" : "text-emerald-600"}`}>
                {data.layer_b.taste_diversity_index}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">채널 편중도</span>
              <span className={`font-semibold ${data.layer_b.viewing_concentration > 0.6 ? "text-rose-600" : "text-emerald-600"}`}>
                {Math.round(data.layer_b.viewing_concentration * 100)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">관심 분야</span>
              <span className="text-xs font-medium text-gray-700">
                {data.top5_interests.slice(0, 3).join(" · ")}
              </span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <LayerBGauge layerB={data.layer_b} />
        </div>
      </div>
    </div>
  );
}

// ── 이상향 섹션 ──────────────────────────────

function IdealSection({
  ideals,
  selected,
  onSelect,
  isLoading,
  error,
  agentMessage,
}: {
  ideals:        IdealRadarChart[];
  selected:      IdealType | null;
  onSelect:      (t: IdealType) => void;
  isLoading:     boolean;
  error:         string | null;
  agentMessage:  string;
}) {
  if (isLoading) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        <p className="text-sm text-gray-500">AI가 이상향을 분석하고 있습니다...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm font-semibold text-red-700">이상향 생성 실패</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
        <p className="mt-2 text-xs text-gray-500">백엔드 서버가 실행 중인지 확인하세요.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-700">이상향 3가지 제안</h3>
        <p className="text-[11px] text-gray-400">
          12차원 추론 (Layer A 8각 + dominant/weak 메타) 기반 자동 생성
        </p>
      </div>

      {agentMessage && (
        <div className="mb-4 rounded-xl border border-blue-100 bg-blue-50 p-4">
          <p className="text-xs text-blue-700 whitespace-pre-line">{agentMessage}</p>
        </div>
      )}

      <IdealSelector
        current={PROFILER_DATA.layer_a}
        ideals={ideals}
        selected={selected}
        onSelect={onSelect}
      />
    </div>
  );
}

// ── 가이드 & 퀘스트 섹션 ────────────────────

function GuideSection({
  guide,
  quests,
  isLoading,
  error,
}: {
  guide:     Guide | null;
  quests:    Quest[];
  isLoading: boolean;
  error:     string | null;
}) {
  if (isLoading) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        <p className="text-sm text-gray-500">가이드와 퀘스트를 생성하고 있습니다...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm font-semibold text-red-700">가이드 생성 실패</p>
        <p className="mt-1 text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (!guide) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-2 text-center">
        <p className="text-sm text-gray-500">이상향을 선택하고 확정하면 가이드가 생성됩니다.</p>
        <p className="text-xs text-gray-400">이상향 선택 탭으로 이동하세요.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <GuideRoadmap guide={guide} />
      </div>

      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold text-gray-800">🎯 오늘의 퀘스트</h3>
          <span className="text-[11px] text-gray-400">
            총 {quests.reduce((s, q) => s + q.reward_point, 0)}pt 획득 가능
          </span>
        </div>
        <div className="space-y-3">
          {quests.map((q, i) => (
            <QuestCard key={i} quest={q} index={i + 1} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 메인 페이지 ──────────────────────────────

export default function NavigatorPage() {
  const [tab,      setTab]      = useState<Tab>("profile");
  const [selected, setSelected] = useState<IdealType | null>(null);

  // 이상향 제안 상태
  const [designResult,  setDesignResult]  = useState<IdealDesignResponse | null>(null);
  const [designLoading, setDesignLoading] = useState(false);
  const [designError,   setDesignError]   = useState<string | null>(null);

  // 가이드/퀘스트 상태
  const [guide,         setGuide]         = useState<Guide | null>(null);
  const [quests,        setQuests]        = useState<Quest[]>([]);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError,  setConfirmError]  = useState<string | null>(null);
  const [confirmMsg,    setConfirmMsg]    = useState("");

  // ── 마운트 시 이상향 자동 생성 ──
  useEffect(() => {
    async function fetchDesign() {
      setDesignLoading(true);
      setDesignError(null);
      try {
        const result = await designIdeal(PROFILER_DATA, PROFILER_DATA.top5_interests);
        setDesignResult(result);
        // expansion 타입이 있으면 기본 선택
        const expansion = result.proposals.find((p) => p.ideal_type === "expansion");
        if (expansion) setSelected("expansion");
      } catch (e) {
        setDesignError(e instanceof Error ? e.message : "이상향 생성 중 오류가 발생했습니다.");
      } finally {
        setDesignLoading(false);
      }
    }
    fetchDesign();
  }, []);

  // ── 이상향 확정 ──
  const handleConfirm = useCallback(async () => {
    if (!selected || !designResult) return;
    const selectedIdeal = designResult.proposals.find((p) => p.ideal_type === selected);
    if (!selectedIdeal) return;

    setConfirmLoading(true);
    setConfirmError(null);
    try {
      const result = await confirmIdeal(PROFILER_DATA, selectedIdeal, PROFILER_DATA.top5_interests);
      setGuide(result.guide);
      setQuests(result.quests);
      setConfirmMsg(result.message);
      setTab("guide");
    } catch (e) {
      setConfirmError(e instanceof Error ? e.message : "가이드 생성 중 오류가 발생했습니다.");
    } finally {
      setConfirmLoading(false);
    }
  }, [selected, designResult]);

  const cognitiveScore = Math.round(
    (PROFILER_DATA.layer_b.search_active_ratio * 100
      + (1 - PROFILER_DATA.layer_b.viewing_concentration) * 100
      + PROFILER_DATA.layer_b.taste_diversity_index
      + PROFILER_DATA.layer_b.exploration_depth * 100) / 4
  );

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      {/* 헤더 */}
      <div className="mb-8">
        <Link
          href={ROUTES.home}
          className="mb-4 inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
        >
          ← 에이전트 목록
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Agent 4</span>
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-700">Dual-Layer</span>
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-bold text-green-700">🔗 API 연결</span>
            </div>
            <h1 className="mt-0.5 text-3xl font-bold tracking-tight text-gray-900">Navigator</h1>
            <p className="mt-1 text-sm text-gray-500">이상향 설계 및 버블 탈출 행동 유도 에이전트</p>
          </div>

          <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-center">
            <p className="text-[10px] font-medium uppercase tracking-wide text-blue-400">인지주권 평균</p>
            <p className="text-2xl font-bold text-blue-700">{cognitiveScore}</p>
            <p className="text-[10px] text-blue-400">/ 100</p>
          </div>
        </div>
      </div>

      {/* 탭 */}
      <div className="mb-6 flex gap-1 rounded-xl border border-gray-200 bg-gray-50 p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-sm font-medium transition-all duration-150 ${
              tab === t.id ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* 탭 컨텐츠 */}
      <div className="min-h-[500px]">
        {tab === "profile" && <ProfileSection />}
        {tab === "ideal" && (
          <IdealSection
            ideals={designResult?.proposals ?? []}
            selected={selected}
            onSelect={setSelected}
            isLoading={designLoading}
            error={designError}
            agentMessage={designResult?.agent_message ?? ""}
          />
        )}
        {tab === "guide" && (
          <GuideSection
            guide={guide}
            quests={quests}
            isLoading={confirmLoading}
            error={confirmError}
          />
        )}
      </div>

      {/* 이상향 확정 버튼 */}
      {tab === "ideal" && selected && !guide && (
        <div className="mt-6 flex items-center justify-between rounded-xl border border-blue-100 bg-blue-50 px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-blue-800">이상향이 선택되었습니다 ✓</p>
            <p className="text-xs text-blue-500">확정하면 30일 가이드와 퀘스트가 생성됩니다</p>
          </div>
          <button
            onClick={handleConfirm}
            disabled={confirmLoading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {confirmLoading ? "생성 중..." : "이상향 확정 →"}
          </button>
        </div>
      )}

      {/* 가이드 생성 완료 메시지 */}
      {confirmMsg && tab === "guide" && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-3">
          <p className="text-sm text-emerald-700">{confirmMsg}</p>
        </div>
      )}

      {/* 가이드 이미 있을 때 이상향 탭에서 안내 */}
      {tab === "ideal" && selected && guide && (
        <div className="mt-6 flex items-center justify-between rounded-xl border border-emerald-100 bg-emerald-50 px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-emerald-800">가이드가 생성되었습니다 ✓</p>
            <p className="text-xs text-emerald-500">가이드 & 퀘스트 탭에서 확인하세요</p>
          </div>
          <button
            onClick={() => setTab("guide")}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors"
          >
            가이드 보기 →
          </button>
        </div>
      )}
    </main>
  );
}
