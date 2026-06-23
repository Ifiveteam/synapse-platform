import {
  CheckCircle2,
  Globe,
  TriangleAlert,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type {
  B2BRecommendations,
  GapAnalysis,
  KeywordItem,
} from "@/api/trend";
import { cn } from "@/lib/utils";

export interface TrendGapDashboardProps {
  macroTrendInternal: KeywordItem[];
  macroTrendExternal: KeywordItem[];
  gapAnalysis: GapAnalysis;
  recommendations: B2BRecommendations;
}

type SourceBadge = {
  label: string;
  variant: "google" | "youtube" | "naver";
};

type ActionTab = "content" | "marketing" | "policy";

const SOURCE_PATTERNS: Array<{ pattern: RegExp; badge: SourceBadge }> = [
  { pattern: /google|구글/i, badge: { label: "Google", variant: "google" } },
  { pattern: /youtube|유튜브/i, badge: { label: "YouTube", variant: "youtube" } },
  { pattern: /naver|네이버/i, badge: { label: "Naver", variant: "naver" } },
];

function detectSourceBadges(metrics: string): SourceBadge[] {
  const matched = SOURCE_PATTERNS.filter(({ pattern }) => pattern.test(metrics)).map(
    ({ badge }) => badge,
  );
  return matched.length > 0 ? matched : [{ label: "외부", variant: "google" }];
}

function changeTone(change: string): string {
  const normalized = change.trim();
  if (/^\+|상승|급등|증가/i.test(normalized)) {
    return "text-emerald-600 dark:text-emerald-400";
  }
  if (/^-|하락|감소|둔화/i.test(normalized)) {
    return "text-rose-600 dark:text-rose-400";
  }
  return "text-muted-foreground";
}

function RankBadge({ rank }: { rank: number }) {
  return (
    <span
      className={cn(
        "inline-flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
        rank === 1 && "bg-amber-100 text-amber-800",
        rank === 2 && "bg-slate-200 text-slate-700",
        rank === 3 && "bg-orange-100 text-orange-800",
        rank > 3 && "bg-muted text-muted-foreground",
      )}
    >
      {rank}
    </span>
  );
}

function KeywordBadges({
  keywords,
  variant,
  emptyLabel,
}: {
  keywords: string[];
  variant: "success" | "indigo" | "orange";
  emptyLabel: string;
}) {
  if (keywords.length === 0) {
    return (
      <span className="text-muted-foreground text-sm">{emptyLabel}</span>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {keywords.map((keyword) => (
        <Badge key={keyword} variant={variant}>
          {keyword}
        </Badge>
      ))}
    </div>
  );
}

function GapSection({
  title,
  keywords,
  interpretation,
  badgeVariant,
  emptyLabel,
}: {
  title: string;
  keywords: string[];
  interpretation: string;
  badgeVariant: "success" | "indigo" | "orange";
  emptyLabel: string;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold">{title}</p>
      <KeywordBadges
        keywords={keywords}
        variant={badgeVariant}
        emptyLabel={emptyLabel}
      />
      <p className="text-muted-foreground text-sm leading-relaxed">
        {interpretation}
      </p>
    </div>
  );
}

function ActionChecklist({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        해당 카테고리 권고 항목이 없습니다.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li
          key={item}
          className="bg-muted/40 flex gap-3 rounded-lg border px-4 py-3 text-sm leading-relaxed"
        >
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function InternalTrendCard({ items }: { items: KeywordItem[] }) {
  return (
    <Card className="h-full border-indigo-100 shadow-sm dark:border-indigo-950">
      <CardHeader className="border-b border-indigo-50 pb-4 dark:border-indigo-950">
        <div className="flex items-center gap-2">
          <div className="flex size-9 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
            <Users className="size-4" />
          </div>
          <div>
            <CardTitle className="text-base">인하우스 유저 픽</CardTitle>
            <CardDescription>플랫폼 내부 코호트 상위 키워드 TOP 5</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-12">순위</TableHead>
              <TableHead>키워드</TableHead>
              <TableHead className="text-right">빈도</TableHead>
              <TableHead className="text-right">변화</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={`internal-${item.rank}-${item.keyword}`}>
                <TableCell>
                  <RankBadge rank={item.rank} />
                </TableCell>
                <TableCell className="font-medium">{item.keyword}</TableCell>
                <TableCell className="text-muted-foreground text-right tabular-nums">
                  {item.metrics}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-right text-xs font-medium tabular-nums",
                    changeTone(item.change),
                  )}
                >
                  {item.change}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ExternalTrendCard({ items }: { items: KeywordItem[] }) {
  return (
    <Card className="h-full border-orange-100 shadow-sm dark:border-orange-950">
      <CardHeader className="border-b border-orange-50 pb-4 dark:border-orange-950">
        <div className="flex items-center gap-2">
          <div className="flex size-9 items-center justify-center rounded-lg bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300">
            <Globe className="size-4" />
          </div>
          <div>
            <CardTitle className="text-base">외부 매크로 트렌드</CardTitle>
            <CardDescription>시장 급상승 키워드 TOP 5</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-12">순위</TableHead>
              <TableHead>키워드</TableHead>
              <TableHead>출처</TableHead>
              <TableHead className="text-right">지표</TableHead>
              <TableHead className="text-right">변화</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={`external-${item.rank}-${item.keyword}`}>
                <TableCell>
                  <RankBadge rank={item.rank} />
                </TableCell>
                <TableCell className="font-medium">{item.keyword}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {detectSourceBadges(item.metrics).map((source) => (
                      <Badge key={source.label} variant={source.variant}>
                        {source.label}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground text-right text-xs tabular-nums">
                  {item.metrics}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-right text-xs font-medium tabular-nums",
                    changeTone(item.change),
                  )}
                >
                  {item.change}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export function TrendGapDashboard({
  macroTrendInternal,
  macroTrendExternal,
  gapAnalysis,
  recommendations,
}: TrendGapDashboardProps) {
  return (
    <section className="flex flex-col gap-6">
      <div className="space-y-1">
        <h2 className="text-xl font-bold tracking-tight">트렌드 대결 보드</h2>
        <p className="text-muted-foreground text-sm">
          내부 코호트 소비 신호와 외부 매크로 트렌드의 격차를 한눈에 비교합니다.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <InternalTrendCard items={macroTrendInternal} />
        <ExternalTrendCard items={macroTrendExternal} />
      </div>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">격차 하이라이트</CardTitle>
          <CardDescription>
            교집합·단절 키워드를 색상 코드로 구분하고 B2B 관점 해석을 제공합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-3">
          <GapSection
            title="교집합 — 내부·외부 공통 관심"
            keywords={gapAnalysis.intersection_keywords}
            interpretation={gapAnalysis.intersection_interpretation}
            badgeVariant="success"
            emptyLabel="공통 키워드 없음"
          />
          <GapSection
            title="내부 우세 — 플랫폼 집중"
            keywords={gapAnalysis.internal_only_keywords}
            interpretation={gapAnalysis.internal_only_interpretation}
            badgeVariant="indigo"
            emptyLabel="내부 우세 키워드 없음"
          />
          <GapSection
            title="외부 우세 — 시장 단독 반응"
            keywords={gapAnalysis.external_only_keywords}
            interpretation={gapAnalysis.external_only_interpretation}
            badgeVariant="orange"
            emptyLabel="외부 우세 키워드 없음"
          />
        </CardContent>
      </Card>

      <div className="rounded-xl border border-amber-200 bg-amber-50/80 px-5 py-4 dark:border-amber-900 dark:bg-amber-950/40">
        <div className="flex gap-3">
          <TriangleAlert className="mt-0.5 size-5 shrink-0 text-amber-600 dark:text-amber-400" />
          <div className="space-y-1">
            <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              ⚠️ 맥락적 필터 버블 경고
            </p>
            <p className="text-sm leading-relaxed text-amber-900/90 dark:text-amber-100/90">
              {gapAnalysis.filter_bubble_scenario}
            </p>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">액션 플랜 가이드</CardTitle>
          <CardDescription>
            B2B 의사결정자를 위한 카테고리별 실행 권고 사항
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue={"content" satisfies ActionTab}>
            <TabsList className="mb-4 h-auto w-full flex-wrap sm:w-fit">
              <TabsTrigger value="content">📢 콘텐츠 기획</TabsTrigger>
              <TabsTrigger value="marketing">💰 광고/마케팅</TabsTrigger>
              <TabsTrigger value="policy">⚙️ 플랫폼 정책</TabsTrigger>
            </TabsList>

            <TabsContent value="content">
              <ActionChecklist items={recommendations.content_strategy} />
            </TabsContent>
            <TabsContent value="marketing">
              <ActionChecklist items={recommendations.marketing} />
            </TabsContent>
            <TabsContent value="policy">
              <ActionChecklist items={recommendations.platform_policy} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </section>
  );
}
