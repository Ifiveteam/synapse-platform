"use client";

import { CheckCircle2, Mail, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { NotificationPayload } from "@/lib/types/profiler";

interface NotificationBannerProps {
  notification: NotificationPayload;
  onDismiss: () => void;
}

export function NotificationBanner({
  notification,
  onDismiss,
}: NotificationBannerProps) {
  const email = notification.channels.email;
  const mailDetail = email.sent
    ? `${email.from_address} → ${email.recipient_masked} 발송됨`
    : email.attempted
      ? `메일 발송 실패${email.error ? `: ${email.error}` : ""}`
      : `메일 미설정${email.error ? ` (${email.error})` : ""}`;

  return (
    <div
      className="mb-6 flex items-start gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3"
      role="status"
    >
      <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-600" />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-sm font-medium">{notification.message}</p>
        <p className="text-muted-foreground flex items-center gap-1.5 text-xs">
          <Mail className="size-3.5 shrink-0" />
          {mailDetail}
        </p>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="shrink-0"
        onClick={onDismiss}
        aria-label="알림 닫기"
      >
        <X className="size-4" />
      </Button>
    </div>
  );
}
