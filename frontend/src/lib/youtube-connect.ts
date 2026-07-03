/**
 * YouTube 쓰기 권한 연동 — GIS 코드 클라이언트로 youtube 스코프 동의.
 *
 *   1) initCodeClient(popup)로 youtube 스코프 동의 → auth code
 *   2) 백엔드가 code 교환 → 토큰 저장 (재생목록 저장 권한 확보)
 *
 * 재생목록을 처음 "유튜브에 저장"할 때 needs_reconsent면 이 흐름을 태운다.
 */

import { apiFetchAuth } from "@/api/client";
import { getGoogleConfig } from "@/api/takeout";

const GIS_SRC = "https://accounts.google.com/gsi/client";
const YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube";

// GIS 전역 객체는 공식 타입이 없어 런타임 객체로 접근.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type GoogleApi = any;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const el = document.createElement("script");
    el.src = src;
    el.async = true;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error(`스크립트 로드 실패: ${src}`));
    document.head.appendChild(el);
  });
}

async function getYoutubeAuthCode(): Promise<string> {
  const { client_id } = await getGoogleConfig();
  if (!client_id) throw new Error("GOOGLE_CLIENT_ID 미설정 (백엔드 env)");
  await loadScript(GIS_SRC);
  const w = window as unknown as { google: GoogleApi };
  return new Promise<string>((resolve, reject) => {
    const client = w.google.accounts.oauth2.initCodeClient({
      client_id,
      scope: YOUTUBE_SCOPE,
      ux_mode: "popup",
      callback: (resp: { code?: string; error?: string }) => {
        if (resp.error || !resp.code) {
          reject(new Error(resp.error || "동의 취소됨"));
        } else {
          resolve(resp.code);
        }
      },
    });
    client.requestCode();
  });
}

/** youtube 스코프 동의 → 백엔드에 토큰 저장. 동의 취소 시 throw. */
export async function connectYoutube(): Promise<void> {
  const code = await getYoutubeAuthCode();
  await apiFetchAuth("/api/v1/auth/youtube/connect", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}
