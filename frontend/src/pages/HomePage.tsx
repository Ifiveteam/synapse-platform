import { ChatMessages } from "@/components/home/chat-messages";
import { GraphViewPlaceholder } from "@/components/home/graph-view-placeholder";
import { HomeHeader } from "@/components/home/home-header";
import { OrchestratorInput } from "@/components/home/orchestrator-input";
import { TrendHoverOverlay } from "@/components/home/trend-hover-overlay";
import { useChatStore } from "@/stores/chat";

export function HomePage() {
  const hasMessages = useChatStore((s) => s.messages.length > 0);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <HomeHeader />

      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        {hasMessages ? (
          <ChatMessages />
        ) : (
          <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden px-6 pt-6">
            <GraphViewPlaceholder />
            <TrendHoverOverlay />
          </div>
        )}
      </div>

      <OrchestratorInput />
    </div>
  );
}
