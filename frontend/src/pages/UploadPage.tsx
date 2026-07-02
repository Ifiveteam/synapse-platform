import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { UploadPanel } from "@/components/upload/upload-panel";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/routes";

export function UploadPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-full max-w-5xl flex-col px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">업로드</h1>
        <p className="text-muted-foreground mt-1 text-sm">시청 기록 업로드</p>
      </div>

      <UploadPanel className="flex-1" showGuides />

      <div className="mt-6 flex justify-end">
        <Button type="button" className="gap-1.5" onClick={() => navigate(ROUTES.home)}>
          메인으로
          <ArrowRight size={16} />
        </Button>
      </div>
    </div>
  );
}
