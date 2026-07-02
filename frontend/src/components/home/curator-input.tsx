import { ArrowUp, ImagePlus, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { streamCurator } from "@/api/curator";
import type { ChartEntry } from "@/stores/chat";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import { useSidebarStore } from "@/stores/sidebar";

function toBase64(file: File): Promise<{ base64: string; mimeType: string }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const [prefix, base64] = dataUrl.split(",");
      const mimeType = prefix.match(/:(.*?);/)?.[1] ?? file.type;
      resolve({ base64, mimeType });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function CuratorInput() {
  const user = useAuthStore((s) => s.user);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sessionId = useChatStore((s) => s.sessionId);
  const { addUserMessage, startAssistantMessage, appendToken, setStatus, addChartEntry, finishAssistantMessage } =
    useChatStore();

  const loadChats = useSidebarStore((s) => s.loadChats);
  const disabled = !user || isStreaming;
  const [focused, setFocused] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [pendingImage, setPendingImage] = useState<{ previewUrl: string; file: File } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) return;
    if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl);
    setPendingImage({ file, previewUrl: URL.createObjectURL(file) });
  };

  useEffect(() => {
    const onDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes("Files")) {
        e.preventDefault();
        setIsDragging(true);
      }
    };
    const onDragLeave = (e: DragEvent) => {
      if (!e.relatedTarget) setIsDragging(false);
    };
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer?.files[0];
      if (file) handleFileSelect(file);
    };
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, [pendingImage]);

  const removePendingImage = () => {
    if (pendingImage) URL.revokeObjectURL(pendingImage.previewUrl);
    setPendingImage(null);
  };

  const handleSend = async () => {
    const trimmed = value.trim();
    if ((!trimmed && !pendingImage) || disabled) return;

    let imageBase64: string | undefined;
    let imageMimeType: string | undefined;

    if (pendingImage) {
      const result = await toBase64(pendingImage.file);
      imageBase64 = result.base64;
      imageMimeType = result.mimeType;
    }

    const previewUrl = pendingImage?.previewUrl;
    setValue("");
    setPendingImage(null);

    addUserMessage(trimmed, previewUrl);
    const assistantId = startAssistantMessage();

    try {
      for await (const chunk of streamCurator(trimmed, sessionId, imageBase64, imageMimeType)) {
        if (chunk.event === "status") {
          setStatus(assistantId, chunk.content);
        } else if (chunk.event === "chart") {
          try {
            const entry = JSON.parse(chunk.content) as ChartEntry;
            addChartEntry(assistantId, entry);
          } catch {
            // ignore malformed chart data
          }
        } else {
          appendToken(assistantId, chunk.content);
        }
      }
    } catch {
      appendToken(assistantId, "❌ 오류가 발생했습니다.");
    } finally {
      finishAssistantMessage(assistantId);
      void loadChats();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <>
      {/* 드래그 오버레이 */}
      {isDragging && (
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-primary p-10 text-primary">
            <ImagePlus size={40} strokeWidth={1.5} />
            <p className="text-base font-medium">이미지를 놓으세요</p>
          </div>
        </div>
      )}

      <div className="shrink-0 px-6 pb-6 pt-3">
        {/* 이미지 미리보기 */}
        {pendingImage && (
          <div className="mb-2 inline-block">
            <div className="relative">
              <img
                src={pendingImage.previewUrl}
                alt=""
                className="h-20 rounded-xl object-cover shadow-md"
              />
              <button
                type="button"
                onClick={removePendingImage}
                className="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full bg-foreground text-background shadow"
              >
                <X size={10} />
              </button>
            </div>
          </div>
        )}

        <div
          className={`border-border flex items-center gap-3 rounded-2xl border bg-card px-4 py-3 shadow-[0_8px_32px_-4px_rgba(0,0,0,0.18)] ring-1 ring-black/5 outline-none dark:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.5)] dark:ring-white/5 ${
            disabled && !isStreaming ? "opacity-70" : ""
          }`}
          style={focused ? { animation: "input-wave 1.2s ease-out infinite" } : undefined}
        >
          <Search size={18} className="text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={
              !user
                ? "로그인 후 큐레이터와 대화할 수 있습니다."
                : isStreaming
                  ? "답변 생성 중..."
                  : "큐레이터에게 무엇이든 물어보세요..."
            }
            className="placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none focus:outline-none disabled:cursor-not-allowed"
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
          />

          {/* 이미지 첨부 버튼 */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="text-muted-foreground hover:text-foreground flex size-8 shrink-0 items-center justify-center rounded-full transition-colors disabled:pointer-events-none disabled:opacity-50"
            title="이미지 첨부"
          >
            <ImagePlus size={16} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileSelect(file);
              e.target.value = "";
            }}
          />

          <Button
            type="button"
            size="icon"
            className="size-8 shrink-0 rounded-full"
            disabled={disabled || (!value.trim() && !pendingImage)}
            onClick={() => void handleSend()}
          >
            <ArrowUp size={16} />
          </Button>
        </div>
      </div>
    </>
  );
}
