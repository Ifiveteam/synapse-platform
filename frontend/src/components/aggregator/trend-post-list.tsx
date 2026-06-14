import { ChevronRight, FileText, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { TrendPostSummary } from "@/api/trend";
import { ROUTES } from "@/routes";

interface TrendPostListProps {
  agentSlug: string;
  posts: TrendPostSummary[];
}

function formatGeneratedAt(iso: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(iso));
}

export function TrendPostList({ agentSlug, posts }: TrendPostListProps) {
  if (posts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>발행된 리포트가 없습니다</CardTitle>
          <CardDescription>
            에이전트 화면에서 트렌드 분석을 실행하면 리포트가 이곳에
            표시됩니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline">
            <Link to={ROUTES.agentDetail(agentSlug)}>에이전트로 돌아가기</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <ul className="space-y-4">
      {posts.map((post) => (
        <li key={post.post_id}>
          <Link to={ROUTES.trendPost(agentSlug, post.post_id)}>
            <Card className="transition-shadow hover:shadow-md">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <FileText className="text-muted-foreground size-4 shrink-0" />
                      시장 인지 성향 분석 보고서
                    </CardTitle>
                    <CardDescription>
                      {formatGeneratedAt(post.generated_at)}
                    </CardDescription>
                  </div>
                  <ChevronRight className="text-muted-foreground mt-1 size-5 shrink-0" />
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="text-muted-foreground flex flex-wrap items-center gap-4 text-sm">
                  <span className="flex items-center gap-1.5">
                    <Users className="size-3.5" />
                    코호트 {post.cohort_size.toLocaleString("ko-KR")}명
                  </span>
                  <span className="font-mono text-xs">
                    ID: {post.post_id.slice(0, 8)}…
                  </span>
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
