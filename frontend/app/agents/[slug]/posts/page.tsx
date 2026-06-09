import Link from "next/link";
import { notFound } from "next/navigation";

import { TrendPostList } from "@/components/aggregator/trend-post-list";
import { Button } from "@/components/ui/button";
import { fetchTrendPosts, type TrendPostSummary } from "@/lib/api/trend";
import { getAgent } from "@/lib/agents";
import { ROUTES } from "@/lib/routes";

interface TrendPostsPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: TrendPostsPageProps) {
  const { slug } = await params;
  const agent = getAgent(slug);

  if (!agent) {
    return { title: "Posts Not Found" };
  }

  return {
    title: `발행 리포트 목록 | ${agent.name}`,
    description: `${agent.name} 에이전트가 발행한 B2B 트렌드 분석 리포트 목록`,
  };
}

export default async function TrendPostsPage({ params }: TrendPostsPageProps) {
  const { slug } = await params;

  if (slug !== "aggregator") {
    notFound();
  }

  const agent = getAgent(slug);

  if (!agent) {
    notFound();
  }

  let posts: TrendPostSummary[] = [];
  let fetchError: string | null = null;

  try {
    const data = await fetchTrendPosts();
    posts = data.items;
  } catch (cause) {
    fetchError =
      cause instanceof Error
        ? cause.message
        : "게시글 목록을 불러오지 못했습니다.";
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-6 py-12">
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="w-fit px-0">
          <Link href={ROUTES.agentDetail(slug)}>← {agent.name}으로 돌아가기</Link>
        </Button>
        <div>
          <p className="text-muted-foreground text-sm font-medium">
            {agent.name} · 트렌드 게시판
          </p>
          <h1 className="text-3xl font-bold tracking-tight">발행된 리포트</h1>
          <p className="text-muted-foreground mt-2 text-sm">
            총 {posts.length.toLocaleString("ko-KR")}건의 B2B 분석 리포트
          </p>
        </div>
      </div>

      {fetchError ? (
        <div
          className="border-destructive/40 bg-destructive/5 text-destructive rounded-lg border p-4 text-sm"
          role="alert"
        >
          <p className="font-medium">목록을 불러올 수 없습니다</p>
          <p className="mt-1">{fetchError}</p>
          <p className="text-muted-foreground mt-2">
            백엔드 Docker 이미지를 최신 코드로 다시 빌드했는지 확인해 주세요.
          </p>
        </div>
      ) : (
        <TrendPostList agentSlug={slug} posts={posts} />
      )}
    </main>
  );
}
