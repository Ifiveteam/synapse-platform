import { useEffect, useRef, useState } from "react";
import { Camera, X } from "lucide-react";

import { toast } from "sonner";

import { updateMe } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";

interface ProfileEditModalProps {
  open: boolean;
  onClose: () => void;
}

export function ProfileEditModal({ open, onClose }: ProfileEditModalProps) {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);
  const setUser = useAuthStore((s) => s.setUser);

  const [nickname, setNickname] = useState(user?.name ?? "");
  const [picturePreview, setPicturePreview] = useState<string | null>(
    user?.picture ?? null,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setNickname(user?.name ?? "");
    setPicturePreview(user?.picture ?? null);
    setError(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose, user?.name, user?.picture]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setPicturePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  async function handleSave() {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateMe(token, {
        nickname,
        picture: picturePreview ?? undefined,
      });
      if (updated) {
        setUser({ ...user!, name: updated.name, picture: updated.picture });
        toast.success("프로필이 저장되었습니다");
        onClose();
      } else {
        setError("저장에 실패했습니다.");
        toast.error("프로필 저장에 실패했습니다");
      }
    } catch {
      setError("저장 중 오류가 발생했습니다.");
      toast.error("저장 중 오류가 발생했습니다");
    } finally {
      setSaving(false);
    }
  }

  const initials = (user?.name ?? "?").slice(0, 2).toUpperCase();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="닫기"
        className="absolute inset-0 bg-slate-900/20 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div className="relative w-full max-w-sm rounded-2xl bg-card shadow-xl">
        <button
          type="button"
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground hover:bg-secondary absolute -top-3 -right-3 z-10 flex size-8 items-center justify-center rounded-full bg-card shadow-md transition-colors"
          aria-label="닫기"
        >
          <X size={16} />
        </button>

        <div className="p-6">
          <h2 className="mb-5 text-base font-semibold">프로필 수정</h2>

          {/* 프로필 사진 */}
          <div className="mb-5 flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="group relative size-20 overflow-hidden rounded-full bg-secondary transition-opacity hover:opacity-80"
            >
              {picturePreview ? (
                <img
                  src={picturePreview}
                  alt="프로필 사진"
                  className="size-full object-cover"
                />
              ) : (
                <span className="flex size-full items-center justify-center text-xl font-semibold text-muted-foreground">
                  {initials}
                </span>
              )}
              <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                <Camera size={20} className="text-white" />
              </div>
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              사진 변경
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-muted-foreground text-xs font-medium">
                닉네임
              </label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !saving) handleSave();
                }}
                className="border-border bg-background focus:ring-ring w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2"
                placeholder="닉네임을 입력하세요"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-muted-foreground text-xs font-medium">
                이메일
              </label>
              <input
                type="text"
                value={user?.email ?? ""}
                readOnly
                className="border-border bg-muted text-muted-foreground w-full cursor-not-allowed rounded-lg border px-3 py-2 text-sm"
              />
            </div>

            {error && <p className="text-destructive text-xs">{error}</p>}
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onClose}
              disabled={saving}
            >
              취소
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !nickname.trim()}
            >
              {saving ? "저장 중..." : "저장"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
