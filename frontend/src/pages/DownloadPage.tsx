import { Link } from "react-router-dom";
import {
  Chrome,
  Download,
  ExternalLink,
  Link2,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/routes";

// ── 확장 프로그램 메타 (배포 시 값만 교체) ──────────────────────────
// TODO: 실제 배포 URL로 교체. 빈 문자열이면 버튼이 "준비 중"으로 표시됩니다.
const EXTENSION = {
  name: "Synapse Scraper",
  version: "1.0.0",
  description:
    "브라우저에서 보던 웹 페이지를 바로 스크랩하고, 로그인한 Synapse 계정과 연동합니다. " +
    "수집한 내용은 플랫폼의 분석·그래프에 반영됩니다.",
  chromeMinVersion: "120",
  downloadUrl: "", // 확장 프로그램 zip 다운로드 링크
  storeUrl: "", // Chrome 웹 스토어 게시 후 URL
  updatedAt: "2026.06",
} as const;

const INSTALL_STEPS = [
  "위 「확장 프로그램 받기」로 zip 파일을 내려받아 압축을 풉니다.",
  "Chrome 주소창에 chrome://extensions 를 입력해 엽니다.",
  "우측 상단의 「개발자 모드」를 켭니다.",
  "「압축해제된 확장 프로그램을 로드합니다」를 누르고 압축 푼 폴더를 선택합니다.",
  "확장 프로그램을 고정한 뒤, Synapse에 로그인하면 자동으로 연동됩니다.",
] as const;

export function DownloadPage() {
  const hasDownload = EXTENSION.downloadUrl.length > 0;
  const hasStore = EXTENSION.storeUrl.length > 0;

  return (
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col px-6 py-8">
      <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
        <Link to={ROUTES.home} className="hover:text-foreground transition-colors">
          홈
        </Link>
        <span>/</span>
        <span className="text-foreground">Chrome 확장 프로그램</span>
      </nav>

      {/* 히어로 */}
      <div className="border-border mb-6 rounded-2xl border bg-card p-6">
        <div className="flex items-start gap-4">
          <div className="bg-primary/10 text-primary flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl">
            <Chrome size={28} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                {EXTENSION.name}
              </h1>
              <Badge variant="outline" className="rounded-full">
                v{EXTENSION.version}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
              {EXTENSION.description}
            </p>
            <p className="text-muted-foreground mt-2 text-xs">
              Chrome {EXTENSION.chromeMinVersion}+ · 업데이트 {EXTENSION.updatedAt}
            </p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {hasDownload ? (
            <Button className="gap-1.5" asChild>
              <a href={EXTENSION.downloadUrl} download>
                <Download size={16} />
                확장 프로그램 받기
              </a>
            </Button>
          ) : (
            <Button className="gap-1.5" disabled>
              <Download size={16} />
              확장 프로그램 받기 (준비 중)
            </Button>
          )}

          {hasStore ? (
            <Button variant="outline" className="gap-1.5" asChild>
              <a href={EXTENSION.storeUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink size={16} />
                Chrome 웹 스토어
              </a>
            </Button>
          ) : (
            <Button variant="outline" className="gap-1.5" disabled>
              <ExternalLink size={16} />
              웹 스토어 (준비 중)
            </Button>
          )}
        </div>
      </div>

      {/* 설치 방법 */}
      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold">설치 방법</h2>
        <ol className="border-border space-y-3 rounded-2xl border bg-card p-5">
          {INSTALL_STEPS.map((step, i) => (
            <li key={step} className="flex gap-3 text-sm">
              <span className="bg-accent text-accent-foreground flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold">
                {i + 1}
              </span>
              <span className="text-muted-foreground leading-relaxed">{step}</span>
            </li>
          ))}
        </ol>
      </section>

      {/* 연동 안내 */}
      <section className="border-border flex items-start gap-3 rounded-2xl border bg-card p-5">
        <div className="bg-accent text-accent-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
          <Link2 size={18} />
        </div>
        <div className="min-w-0 flex-1 text-sm">
          <p className="font-medium">웹과 연동하기</p>
          <p className="text-muted-foreground mt-1 leading-relaxed">
            확장 프로그램을 설치한 뒤 Synapse에 로그인하면 계정이 자동으로 연결됩니다.
            아직 로그인하지 않았다면 먼저 로그인해 주세요.
          </p>
          <Button variant="link" className="mt-1 h-auto gap-1 px-0 text-sm" asChild>
            <Link to={ROUTES.home}>
              로그인하러 가기
              <ExternalLink size={13} />
            </Link>
          </Button>
        </div>
      </section>

      <p className="text-muted-foreground mt-4 flex items-center gap-1.5 text-xs">
        <ShieldCheck size={13} />
        수집 데이터는 본인 계정에만 연동되며, 설치형(압축해제) 버전은 개발자 모드가 필요합니다.
      </p>
    </div>
  );
}
