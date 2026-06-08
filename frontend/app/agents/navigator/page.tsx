"use client";

import { useState } from "react";
import Link from "next/link";
import {
  MOCK_GUIDE,
  MOCK_IDEAL_BALANCED,
  MOCK_IDEAL_EXPANSION,
  MOCK_IDEAL_OPPOSITE,
  MOCK_PROFILER_DATA,
  MOCK_QUESTS,
} from "@/lib/navigator-mock";
import type { IdealType, IdealRadarChart } from "@/lib/navigator-types";
import { NavigatorRadarChart } from "@/components/navigator/radar-chart";
import { LayerBGauge } from "@/components/navigator/layer-b-gauge";
import { AXIS_LABELS } from "@/lib/navigator-types";
import { IdealSelector } from "@/components/navigator/ideal-selector";
import { GuideRoadmap, QuestCard } from "@/components/navigator/quest-card";
import { ROUTES } from "@/lib/routes";

// ── 탭 정의 ──────────────────────────────────

type Tab = "profile" | "ideal" | "guide";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "profile", label: "현재 프로필", icon: "📊" },
  { id: "ideal",   label: "이상향 선택", icon: "🎯" },
  { id: "guide",   label: "가이드 & 퀘스트", icon: "🗺️" },
];

const ALL_IDEALS: IdealRadarChart[] = [
  MOCK_IDEAL_OPPOSITE,
  MOCK_IDEAL_EXPANSION,
  MOCK_IDEAL_BALANCED,
];

// ── 프로필 섹션 ──────────────────────────────

/** layer_a 점수에서 dominant / weak 축 계산 (threshold=15) */
function computeDominantWeak(layerA: Record<string, number>, threshold = 15) {
  const entries = Object.entries(layerA).filter(([k]) => k !== "user_id");
  const mean    = entries.reduce((s, [, v]) => s + v, 0) / entries.length;
  const sorted  = [...entries].sort((a, b) => b[1] - a[1]);
  const dominant = sorted.slice(0, 2).filter(([, v]) => v >= mean + threshold / 2).map(([k]) => k);
  const weakSorted = [...entries].sort((a, b) => a[1] - b[1]);
  const weak    = weakSorted.slice(0, 2).filter(([, v]) => v <= mean - threshold / 2).map(([k]) => k);
  return { dominant, weak };
}

function ProfileSection() {
  const data = MOCK_PROFILER_DATA;
  const { dominant, weak } = computeDominantWeak(data.layer_a as unknown as Record<string, number>);

  const dominantLabels = dominant.map((a) => AXIS_LABELS[a as keyof typeof AXIS_LABELS] ?? a).join(", ");
  const weakLabels     = weak.map((a) => AXIS_LABELS[a as keyof typeof AXIS_LABELS] ?? a).join(", ");

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      {/* 레이더 차트 */}
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-1 text-sm font-semibold text-gray-700">
          Layer A — Profiler 8각
        </h3>
        <p className="mb-4 text-[11px] text-gray-400">
          YouTube 콘텐츠 소비 행동 측정값 (Profiler v1.1)
        </p>
        <NavigatorRadarChart current={data.layer_a} size={340} />
      </div>

      {/* 우측 패널 */}
      <div className="flex flex-col gap-4">
        {/* Profiler 메타 (v1.1: layer_a 기반 런타임 계산) */}
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">
            프로필 분석
          </h4>
          <div className="space-y-1.5">
            <div>
              <span className="text-[10px] font-semibold text-rose-500">
                주 성향축 ▲
              </span>
              <p className="text-xs text-gray-600">{dominantLabels || "—"}</p>
            </div>
            <div>
              <span className="text-[10px] font-semibold text-blue-500">
                공백축 ▽
              </span>
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

        {/* Layer B 게이지 */}
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <LayerBGauge layerB={data.layer_b} />
        </div>
      </div>
    </div>
  );
}

// ── 이상향 섹션 ──────────────────────────────

function IdealSection({
  selected,
  onSelect,
}: {
  selected: IdealType | null;
  onSelect: (t: IdealType) => void;
}) {
  return (
    <div>
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-700">
          이상향 3가지 제안
        </h3>
        <p className="text-[11px] text-gray-400">
          12차원 추론 (Layer A 8각 + dominant/weak 메타) 기반 자동 생성
        </p>
      </div>
      <IdealSelector
        current={MOCK_PROFILER_DATA.layer_a}
        ideals={ALL_IDEALS}
        selected={selected}
        onSelect={onSelect}
      />
    </div>
  );
}

// ── 가이드 & 퀘스트 섹션 ──────────────────────

function GuideSection() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      {/* 로드맵 */}
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <GuideRoadmap guide={MOCK_GUIDE} />
      </div>

      {/* 오늘의 퀘스트 */}
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold text-gray-800">🎯 오늘의 퀘스트</h3>
          <span className="text-[11px] text-gray-400">
            총 {MOCK_QUESTS.reduce((s, q) => s + q.reward_point, 0)}pt 획득 가능
          </span>
        </div>
        <div className="space-y-3">
          {MOCK_QUESTS.map((q, i) => (
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
  const [selected, setSelected] = useState<IdealType | null>("expansion");

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
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">
                Agent 4
              </span>
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-700">
                Dual-Layer
              </span>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                🚧 개발 중
              </span>
            </div>
            <h1 className="mt-0.5 text-3xl font-bold tracking-tight text-gray-900">
              Navigator
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              이상향 설계 및 버블 탈출 행동 유도 에이전트
            </p>
          </div>

          {/* Layer B 평균 뱃지 */}
          <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-center">
            <p className="text-[10px] font-medium uppercase tracking-wide text-blue-400">
              인지주권 평균
            </p>
            <p className="text-2xl font-bold text-blue-700">
              {Math.round(
                (MOCK_PROFILER_DATA.layer_b.search_active_ratio * 100
                  + (1 - MOCK_PROFILER_DATA.layer_b.viewing_concentration) * 100
                  + MOCK_PROFILER_DATA.layer_b.taste_diversity_index
                  + MOCK_PROFILER_DATA.layer_b.exploration_depth * 100) / 4
              )}
            </p>
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
              tab === t.id
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
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
          <IdealSection selected={selected} onSelect={setSelected} />
        )}
        {tab === "guide" && <GuideSection />}
      </div>

      {/* 하단 - 이상향 선택 시 다음 단계 유도 */}
      {tab === "ideal" && selected && (
        <div className="mt-6 flex items-center justify-between rounded-xl border border-blue-100 bg-blue-50 px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-blue-800">
              이상향이 선택되었습니다 ✓
            </p>
            <p className="text-xs text-blue-500">
              가이드와 퀘스트를 확인해보세요
            </p>
          </div>
          <button
            onClick={() => setTab("guide")}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            가이드 보기 →
          </button>
        </div>
      )}

      {/* 개발 중 안내 배너 */}
      <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-lg">🚧</span>
          <div>
            <p className="text-sm font-semibold text-amber-800">
              현재 개발 중인 기능입니다
            </p>
            <ul className="mt-1.5 space-y-0.5 text-[11px] text-amber-700">
              <li>• 화면의 모든 데이터는 Mock(임시) 데이터입니다 — 실제 분석 결과가 아닙니다</li>
              <li>• DB 저장 기능 미구현 — 새로고침 시 초기화됩니다</li>
              <li>• 대화형 이상향 설계(Chat)는 OpenAI API 키 연결 후 동작합니다</li>
              <li>• YouTube 알고리즘 변형 기능은 Extension 개발 완료 후 활성화됩니다</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}
