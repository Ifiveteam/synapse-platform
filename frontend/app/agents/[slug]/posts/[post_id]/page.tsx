import { notFound } from "next/navigation";

import { TrendPostDashboard } from "@/components/aggregator/trend-post-dashboard";
import { fetchTrendPost } from "@/lib/api/trend";
import { getAgent } from "@/lib/agents";

interface TrendPostPageProps {
  params: Promise<{ slug: string; post_id: string }>;
}

export async function generateMetadata({ params }: TrendPostPageProps) {
  const { slug } = await params;
  const agent = getAgent(slug);

  if (!agent) {
    return { title: "Report Not Found" };
  }

  return {
    title: `트렌드 분석 리포트 | ${agent.name}`,
    description: `${agent.name} 에이전트가 생성한 B2B 트렌드 분석 보고서`,
  };
}

export default async function TrendPostPage({ params }: TrendPostPageProps) {
  const { slug, post_id } = await params;
  const agent = getAgent(slug);

  if (!agent) {
    notFound();
  }

  let post;

  try {
    post = await fetchTrendPost(post_id);
  } catch {
    notFound();
  }

  return <TrendPostDashboard agentSlug={slug} post={post} />;
}
