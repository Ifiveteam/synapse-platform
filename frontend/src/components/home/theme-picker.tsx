import { Palette } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { CHAT_THEMES, useChatThemeStore } from "@/stores/chat-theme";

export function ThemePicker() {
  const [open, setOpen] = useState(false);
  const { themeId, setTheme } = useChatThemeStore();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-muted-foreground hover:text-foreground flex size-8 items-center justify-center rounded-full transition-colors"
        title="테마 변경"
      >
        <Palette size={16} />
      </button>

      {open && (
        <div className="absolute bottom-14 right-0 z-50 w-72 rounded-2xl border border-border bg-card p-4 shadow-2xl">
          <p className="mb-3 text-xs font-semibold text-muted-foreground">채팅 테마 선택</p>
          <div className="grid grid-cols-5 gap-3">
            {CHAT_THEMES.map((theme) => (
              <button
                key={theme.id}
                type="button"
                onClick={() => { setTheme(theme.id); setOpen(false); }}
                title={theme.name}
                className="group flex items-center justify-center"
              >
                <div
                  className={`size-11 rounded-full shadow-md transition-all duration-150 group-hover:scale-110 ${
                    themeId === theme.id
                      ? "scale-110 ring-2 ring-offset-2 ring-foreground/50"
                      : ""
                  }`}
                  style={{ background: theme.bubble }}
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
