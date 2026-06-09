"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AXIS_LABELS, LAYER_B_LABELS } from "@/lib/profiler/labels";
import type { ProfilerResult } from "@/lib/types/profiler";
import { SYNAPSE_AXIS_KEYS } from "@/lib/types/profiler";

interface ProfileResultsProps {
  result: ProfilerResult;
}

function LayerBGauge({
  label,
  value,
  max,
  format,
}: {
  label: string;
  value: number;
  max: number;
  format: (v: number) => string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground font-mono">{format(value)}</span>
      </div>
      <div className="bg-muted h-2 overflow-hidden rounded-full">
        <div
          className="bg-primary h-full rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function ProfileResults({ result }: ProfileResultsProps) {
  const radarData = SYNAPSE_AXIS_KEYS.map((key) => ({
    axis: AXIS_LABELS[key],
    value: result.axes[key],
  }));

  const { interpretation, layer_b: layerB } = result;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Synapse 8각</CardTitle>
            <CardDescription>Layer A — 콘텐츠 취향 레이더</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid />
                <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} />
                <Radar
                  name="점수"
                  dataKey="value"
                  stroke="#171717"
                  fill="#171717"
                  fillOpacity={0.35}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Layer B</CardTitle>
            <CardDescription>인지주권 4지표</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <LayerBGauge
              label={LAYER_B_LABELS.search_active_ratio}
              value={layerB.search_active_ratio}
              max={1}
              format={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <LayerBGauge
              label={LAYER_B_LABELS.viewing_concentration}
              value={layerB.viewing_concentration}
              max={1}
              format={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <LayerBGauge
              label={LAYER_B_LABELS.taste_diversity_index}
              value={layerB.taste_diversity_index}
              max={100}
              format={(v) => `${v.toFixed(1)}`}
            />
            <LayerBGauge
              label={LAYER_B_LABELS.exploration_depth}
              value={layerB.exploration_depth}
              max={1}
              format={(v) => `${(v * 100).toFixed(0)}%`}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">해석</CardTitle>
          <CardDescription>
            소비 유형 · {interpretation.consumption_mode} · 인지주권{" "}
            {interpretation.sovereignty_verdict}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            <span className="text-muted-foreground">개선 레버:</span>{" "}
            {interpretation.primary_lever}
          </p>
          <p className="leading-relaxed">{interpretation.radar_gap_insight}</p>
          <p className="text-muted-foreground leading-relaxed border-t pt-3">
            {result.summary}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">TOP5 관심사</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3">
            {result.top5_interests.map((item) => (
              <li key={item.rank} className="flex gap-3 text-sm">
                <span className="text-muted-foreground w-6 font-mono">
                  {item.rank}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{item.label}</p>
                  {item.evidence.length > 0 && (
                    <p className="text-muted-foreground truncate text-xs">
                      {item.evidence.join(" · ")}
                    </p>
                  )}
                </div>
                <span className="text-muted-foreground font-mono text-xs">
                  {(item.score * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {result.behavior_patterns && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">행동 패턴</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <p className="text-muted-foreground mb-2">시간대 분포</p>
              <ul className="space-y-1 font-mono text-xs">
                {Object.entries(result.behavior_patterns.hour_distribution).map(
                  ([bucket, ratio]) => (
                    <li key={bucket}>
                      {bucket}: {(ratio * 100).toFixed(0)}%
                    </li>
                  ),
                )}
              </ul>
            </div>
            <div>
              <p className="text-muted-foreground mb-2">
                주말 비율:{" "}
                {(result.behavior_patterns.weekend_ratio * 100).toFixed(0)}%
              </p>
              <p className="text-muted-foreground mb-1">반복 채널</p>
              <ul className="space-y-1 text-xs">
                {result.behavior_patterns.top_repeated_channels
                  .slice(0, 4)
                  .map((ch) => (
                    <li key={ch.channel}>
                      {ch.channel} ({ch.count})
                    </li>
                  ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
