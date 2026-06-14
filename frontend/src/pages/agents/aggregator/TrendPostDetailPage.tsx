import { useEffect, useState } from "react";
import { useParams, Navigate } from "react-router-dom";

import { fetchTrendPost, type TrendPostResponse } from "@/api/trend";
import { TrendPostDashboard } from "@/components/aggregator/trend-post-dashboard";
import { getAgent } from "@/lib/agents";
import { ROUTES } from "@/routes";

export function TrendPostDetailPage() {
  const { slug = "", postId = "" } = useParams();
  const [post, setPost] = useState<TrendPostResponse | null>(null);
  const [notFound, setNotFound] = useState(false);

  const agent = getAgent(slug);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchTrendPost(postId);
        if (!cancelled) setPost(data);
      } catch {
        if (!cancelled) setNotFound(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [postId]);

  if (!agent || notFound) {
    return <Navigate to={ROUTES.home} replace />;
  }

  if (!post) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6 py-12">
        <p className="text-muted-foreground text-sm">리포트를 불러오는 중…</p>
      </main>
    );
  }

  return <TrendPostDashboard agentSlug={slug} post={post} />;
}
