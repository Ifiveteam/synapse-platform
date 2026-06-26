import { issueExtensionAuthCode } from "@/api/auth";
import { SYNAPSE_WEB_MESSAGE_SOURCE } from "@/lib/auth-protocol";

/**
 * 웹 로그인 세션 → 1회용 code → 익스텐션이 백엔드와 직접 토큰 교환.
 * Synapse 웹 탭에 content script가 주입되어 있어야 동작한다.
 */
export async function syncAuthToExtension(
  accessToken?: string | null,
): Promise<void> {
  const codeResponse = await issueExtensionAuthCode(accessToken);
  if (!codeResponse?.code) return;

  window.postMessage(
    {
      source: SYNAPSE_WEB_MESSAGE_SOURCE,
      type: "AUTH_CODE",
      payload: { code: codeResponse.code },
    },
    window.location.origin,
  );
}

/** 프론트 로그아웃 시 익스텐션 저장 토큰 제거 요청 */
export function clearAuthFromExtension(): void {
  window.postMessage(
    {
      source: SYNAPSE_WEB_MESSAGE_SOURCE,
      type: "AUTH_CLEAR",
    },
    window.location.origin,
  );
}
