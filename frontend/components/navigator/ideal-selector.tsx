"use client";

import { IDEAL_META } from "@/lib/navigator-types";
import type { IdealRadarChart, IdealType, RadarChart } from "@/lib/navigator-types";
import { NavigatorRadarChart } from "./radar-chart";
import { AXIS_LABELS } from "@/lib/navigator-types";

interface IdealSelectorProps {
  current:      RadarChart;
  ideals:       IdealRadarChart[];
  selected:     IdealType | null;
  onSelect:     (type: IdealType) => void;
}

function GapBadge({ gap }: { gap: number }) {
  if (Math.abs(gap) < 3) return null;
  const up    = gap > 0;
  const color = up ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50";
  return (
    <span className={`rounded px-1 py-0.5 text-[10px] font-bold tabular-nums ${color}`}>
      {up ? "+" : ""}{Math.round(gap)}
    </span>
  );
}

function IdealCard({
  ideal,
  current,
  isSelected,
  onClick,
}: {
  ideal:      IdealRadarChart;
  current:    RadarChart;
  isSelected: boolean;
  onClick:    () => void;
}) {
  const meta = IDEAL_META[ideal.ideal_type];
  const axisKeys = [
    "intellectual_curiosity", "self_improvement", "social_awareness",
    "depth_immersion", "practical_orientation", "emotional_comfort",
    "creative_expression", "entertainment_release",
  ] as const;

  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl border-2 p-4 text-left transition-all duration-200 ${meta.color} ${
        isSelected
          ? `${meta.borderColor} shadow-md ring-2 ring-offset-1 ${meta.borderColor.replace("border-", "ring-")}`
          : "border-transparent hover:border-gray-300"
      }`}
    >
      {/* 헤더 */}
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-800">{meta.label}</span>
          {meta.recommended && (
            <span className="rounded-full bg-blue-500 px-2 py-0.5 text-[10px] font-bold text-white">
              추천
            </span>
          )}
        </div>
        {isSelected && (
          <span className="text-xs font-semibold text-gray-600">✓ 선택됨</span>
        )}
      </div>

      <p className="mb-3 text-[11px] text-gray-500">{meta.description}</p>
      <p className="mb-3 text-xs italic text-gray-600">&ldquo;{ideal.summary}&rdquo;</p>

      {/* gap 요약 */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
        {axisKeys.map((k) => {
          const gap = (ideal[k] as number) - (current[k] as number);
          return (
            <div key={k} className="flex items-center justify-between gap-1">
              <span className="truncate text-[10px] text-gray-600">
                {AXIS_LABELS[k]}
              </span>
              <GapBadge gap={gap} />
            </div>
          );
        })}
      </div>
    </button>
  );
}

export function IdealSelector({ current, ideals, selected, onSelect }: IdealSelectorProps) {
  const selectedIdeal = ideals.find((i) => i.ideal_type === selected) ?? null;

  return (
    <div className="space-y-6">
      {/* 이상향 카드 선택 */}
      <div className="grid gap-3 sm:grid-cols-3">
        {ideals.map((ideal) => (
          <IdealCard
            key={ideal.ideal_type}
            ideal={ideal}
            current={current}
            isSelected={selected === ideal.ideal_type}
            onClick={() => onSelect(ideal.ideal_type)}
          />
        ))}
      </div>

      {/* 선택된 이상향 오버레이 레이더 */}
      {selectedIdeal && (
        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h4 className="mb-1 text-center text-sm font-semibold text-gray-700">
            현재 프로필 vs {IDEAL_META[selectedIdeal.ideal_type].label}
          </h4>
          <p className="mb-4 text-center text-[11px] text-gray-400">
            파란 실선 = 현재 · 빨간 점선 = 이상향
          </p>
          <NavigatorRadarChart current={current} ideal={selectedIdeal} size={340} />
        </div>
      )}
    </div>
  );
}
