import { Link } from "react-router-dom";
import { Chrome, Download, ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CHROME_EXTENSION, INSTALL_STEPS } from "@/lib/downloads/mock";
import { ROUTES } from "@/routes";

export function DownloadPage() {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col px-6 py-8">
      <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
        <Link to={ROUTES.home} className="hover:text-foreground transition-colors">
          홈
        </Link>
        <span>/</span>
        <span className="text-foreground">Chrome 확장 프로그램</span>
      </nav>

      <div className="border-border mb-8 rounded-2xl border bg-card p-6">
        <div className="flex items-start gap-4">
          <div className="bg-primary/10 text-primary flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl">
            <Chrome size={28} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                {CHROME_EXTENSION.name}
              </h1>
              <Badge variant="outline" className="rounded-full">
                v{CHROME_EXTENSION.version}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
              {CHROME_EXTENSION.description}
            </p>
            <p className="text-muted-foreground mt-2 text-xs">
              Chrome {CHROME_EXTENSION.chromeMinVersion}+ · 업데이트{" "}
              {CHROME_EXTENSION.updatedAt}
            </p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Button className="gap-1.5">
            <Download size={16} />
            {CHROME_EXTENSION.fileName} 받기
          </Button>
          <Button variant="outline" className="gap-1.5" asChild>
            <a
              href={CHROME_EXTENSION.storeUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink size={16} />
              Chrome 웹 스토어에서 설치
            </a>
          </Button>
        </div>
      </div>

      <section>
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
    </div>
  );
}
