"use client";

import { useState } from "react";
import { AXIS_LABELS, AXIS_TYPES, AXIS_TYPE_COLOR } from "@/lib/navigator-types";
import type { Guide, Quest } from "@/lib/navigator-types";

// ── 퀘스트 카드 ──────────────────────────────

interface QuestCardProps {
  quest: Quest;
  index: number;
}

export function QuestCard({ quest, index }: QuestCardProps) {
  const [done, setDone] = useState(quest.is_completed);
  const axisType  = AXIS_TYPES[quest.target_axis];
  const colorCls  = AXIS_TYPE_COLOR[axisType];

  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-200 ${
        done
          ? "border-gray-200 bg-gray-50 opacity-60"
          : "border-gray-200 bg-white shadow-sm hover:shadow-md"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* 번호 + 제목 */}
        <div className="flex items-start gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600">
            {index}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-bold ${done ? "line-through text-gray-400" : "text-gray-800"}`}>
                {quest.title}
              </span>
              <span className={`text-[10px] font-semibold ${colorCls}`}>
                {AXIS_LABELS[quest.target_axis]}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-gray-500">{quest.description}</p>
          </div>
        </div>

        {/* 포인트 + 완료 */}
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
            +{quest.reward_point}pt
          </span>
          <button
            onClick={() => setDone(!done)}
            className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold transition-colors ${
              done
                ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                : "border-gray-300 text-gray-500 hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700"
            }`}
          >
            {done ? "✓ 완료" : "완료"}
          </button>
        </div>
      </div>

      {/* 액션 */}
      {!done && (
        <div className="mt-3 rounded-lg bg-gray-50 px-3 py-2">
          <p className="text-[11px] font-medium text-gray-500">→ {quest.action}</p>
        </div>
      )}
    </div>
  );
}

// ── 가이드 로드맵 ──────────────────────────────

interface GuideRoadmapProps {
  guide: Guide;
}

export function GuideRoadmap({ guide }: GuideRoadmapProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-800">{guide.title}</h3>
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700">
          {guide.estimated_days}일 플랜
        </span>
      </div>

      {/* 타겟 축 */}
      <div className="flex flex-wrap gap-1.5">
        {guide.target_axes.map((ax) => {
          const type = AXIS_TYPES[ax];
          const colorCls = AXIS_TYPE_COLOR[type];
          return (
            <span
              key={ax}
              className={`rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium ${colorCls}`}
            >
              {AXIS_LABELS[ax]}
            </span>
          );
        })}
      </div>

      {/* 주차별 스텝 */}
      <div className="relative space-y-0">
        {guide.steps.map((step, i) => (
          <div key={i} className="flex gap-3">
            {/* 타임라인 선 */}
            <div className="flex flex-col items-center">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
                {i + 1}
              </div>
              {i < guide.steps.length - 1 && (
                <div className="w-0.5 flex-1 bg-blue-100" style={{ minHeight: "24px" }} />
              )}
            </div>
            {/* 내용 */}
            <div className="pb-5 pt-0.5">
              <p className="text-sm leading-snug text-gray-700">{step}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
