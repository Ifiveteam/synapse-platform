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
import { AXIS_LABELS } from "@/lib/profiler/labels";
import type { DbProfileResponse } from "@/api/types/profiler";
import { SYNAPSE_AXIS_KEYS } from "@/api/types/profiler";

interface ProfileResultsProps {
  result: DbProfileResponse;
}

export function ProfileResults({ result }: ProfileResultsProps) {
  const radarData = SYNAPSE_AXIS_KEYS.map((key) => ({
    axis: AXIS_LABELS[key],
    value: Math.round((result.scores[key] ?? 0) * 100),
  }));

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
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.35}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">분석 요약</CardTitle>
            {result.persona_label && (
              <CardDescription>{result.persona_label}</CardDescription>
            )}
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="leading-relaxed">{result.summary_text}</p>
            {result.behavior_reasoning && (
              <p className="text-muted-foreground border-t pt-3 leading-relaxed">
                {result.behavior_reasoning}
              </p>
            )}
            {result.tone_of_user && (
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">톤:</span> {result.tone_of_user}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {result.dominant_traits && result.dominant_traits.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">주요 성향</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {result.dominant_traits.map((trait) => (
                <span
                  key={trait}
                  className="bg-primary/10 text-primary rounded-full px-3 py-1 text-xs font-medium"
                >
                  {trait}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        {result.top_categories.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top 카테고리</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-2">
                {result.top_categories.slice(0, 5).map((item, i) => (
                  <li key={item.category_id} className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground w-5 font-mono text-xs">{i + 1}</span>
                    <span className="flex-1 truncate">{item.category_id}</span>
                    <span className="text-muted-foreground font-mono text-xs">{item.count}</span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}

        {result.top_channels.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top 채널</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-2">
                {result.top_channels.slice(0, 5).map((item, i) => (
                  <li key={item.channel} className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground w-5 font-mono text-xs">{i + 1}</span>
                    <span className="flex-1 truncate">{item.channel}</span>
                    <span className="text-muted-foreground font-mono text-xs">{item.count}</span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
