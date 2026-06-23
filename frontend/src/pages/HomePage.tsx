import { X } from "lucide-react";

import { ChatMessages } from "@/components/home/chat-messages";
import { GraphViewPlaceholder } from "@/components/home/graph-view-placeholder";
import { HomeHeader } from "@/components/home/home-header";
import { CuratorInput } from "@/components/home/curator-input";
import { TrendHoverOverlay } from "@/components/home/trend-hover-overlay";
import { useChatStore } from "@/stores/chat";

export function HomePage() {
  const hasMessages = useChatStore((s) => s.messages.length > 0);
  const clearMessages = useChatStore((s) => s.clearMessages);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <HomeHeader />

      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        {hasMessages ? (
          <div className="relative flex min-h-0 flex-1 flex-col">
            <button
              type="button"
              onClick={clearMessages}
              title="채팅 닫기"
              className="text-muted-foreground hover:text-foreground hover:bg-secondary absolute right-4 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full transition-colors"
            >
              <X size={15} />
            </button>
            <ChatMessages />
          </div>
        ) : (
          <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden px-6 pt-6">
            <GraphViewPlaceholder />
            <TrendHoverOverlay />
          </div>
        )}
      </div>

      <CuratorInput />
    </div>
  );
}
