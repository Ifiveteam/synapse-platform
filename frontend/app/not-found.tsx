import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ROUTES } from "@/lib/routes";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-6 text-center">
      <h1 className="text-2xl font-bold">에이전트를 찾을 수 없습니다</h1>
      <p className="text-muted-foreground mt-2">
        요청하신 에이전트가 존재하지 않습니다.
      </p>
      <Button asChild className="mt-6">
        <Link href={ROUTES.home}>메인으로 돌아가기</Link>
      </Button>
    </main>
  );
}
