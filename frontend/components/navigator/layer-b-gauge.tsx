"use client";

import { LAYER_B_META } from "@/lib/navigator-types";
import type { ProfilerLayerB, LayerBKey } from "@/lib/navigator-types";

interface LayerBGaugeProps {
  layerB: ProfilerLayerB;
}

function GaugeBar({
  value,
  warn,
  inverted,
}: {
  value: number;       // 0~100 환산 후 값
  warn: boolean;
  inverted: boolean;   // 높을수록 나쁨 여부
}) {
  const pct = Math.round(Math.min(100, Math.max(0, value)));

  // inverted(채널 편중도): 게이지가 찰수록 빨간색
  const color = warn
    ? inverted
      ? "bg-rose-500"
      : "bg-amber-400"
    : pct >= 60
    ? "bg-emerald-500"
    : "bg-blue-500";

  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
      <div
        className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/** 0~1 범위 값을 0~100으로 환산 */
function toDisplay(key: LayerBKey, raw: number): number {
  const meta = LAYER_B_META[key];
  return meta.unit === "ratio" ? Math.round(raw * 100) : Math.round(raw);
}

/** 경보 여부 — invertedPolarity에 따라 방향 반전 */
function isWarning(key: LayerBKey, raw: number): boolean {
  const meta = LAYER_B_META[key];
  return meta.invertedPolarity
    ? raw > meta.warnThreshold          // 높을수록 나쁨: 임계 초과 시 경보
    : raw < meta.warnThreshold;         // 높을수록 좋음: 임계 미만 시 경보
}

export function LayerBGauge({ layerB }: LayerBGaugeProps) {
  const keys = Object.keys(layerB) as LayerBKey[];

  // 건강도 평균: viewing_concentration 역전 후 합산
  const health = Math.round(
    (layerB.search_active_ratio * 100
      + (1 - layerB.viewing_concentration) * 100
      + layerB.taste_diversity_index
      + layerB.exploration_depth * 100
    ) / 4
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">
          Layer B — 인지주권 4지표
        </h3>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500">
          건강도 {health}
        </span>
      </div>

      <div className="space-y-3.5">
        {keys.map((key) => {
          const meta     = LAYER_B_META[key];
          const raw      = layerB[key] as number;
          const display  = toDisplay(key, raw);
          const warn     = isWarning(key, raw);

          return (
            <div key={key} className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-base leading-none">{meta.icon}</span>
                  <span className="text-sm font-medium text-gray-800">
                    {meta.label}
                  </span>
                  {meta.invertedPolarity && (
                    <span className="text-[9px] text-gray-400">(↓좋음)</span>
                  )}
                  {warn && (
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                        meta.invertedPolarity
                          ? "bg-rose-100 text-rose-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {meta.invertedPolarity ? "편중" : "주의"}
                    </span>
                  )}
                </div>
                <span
                  className={`tabular-nums text-sm font-bold ${
                    warn
                      ? meta.invertedPolarity
                        ? "text-rose-600"
                        : "text-amber-600"
                      : "text-gray-700"
                  }`}
                >
                  {meta.unit === "ratio" ? `${display}%` : display}
                </span>
              </div>
              <GaugeBar value={display} warn={warn} inverted={meta.invertedPolarity} />
              <p className="text-[11px] leading-snug text-gray-400">
                {meta.description}
              </p>
            </div>
          );
        })}
      </div>

      <p className="border-t border-dashed border-gray-200 pt-3 text-[10px] leading-relaxed text-gray-400">
        인지주권 4지표는 YouTube 시청·검색 패턴에서 파생된 참고 지표입니다.
        직접 측정값이 아니며 개인의 미디어 이해도를 직접 평가하지 않습니다.
      </p>
    </div>
  );
}
