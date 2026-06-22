import { useEffect, useRef } from "react";

import { useChatStore } from "@/stores/chat";

export function ChatMessages() {
  const messages = useChatStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-4">
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "user" ? (
              <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                {msg.content}
              </div>
            ) : (
              <div className="flex max-w-[85%] flex-col gap-1">
                {msg.status && (
                  <p className="text-muted-foreground px-1 text-xs italic">
                    {msg.status}
                  </p>
                )}
                {(msg.content || !msg.status) && (
                  <div className="rounded-2xl rounded-bl-sm bg-card px-4 py-2.5 text-sm leading-relaxed shadow-sm ring-1 ring-black/5 dark:ring-white/5">
                    {msg.content}
                    {msg.streaming && msg.content && (
                      <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current align-middle opacity-70" />
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
