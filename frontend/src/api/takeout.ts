import { apiFetch, apiFetchAuth } from "@/api/client";

export interface GoogleConfig {
  client_id: string;
  picker_api_key: string;
}

let googleConfigCache: Promise<GoogleConfig> | null = null;

/** Picker용 공개 설정(client_id + api key)을 백엔드 env에서 받아온다 (1회 캐시). */
export function getGoogleConfig(): Promise<GoogleConfig> {
  if (!googleConfigCache) {
    googleConfigCache = apiFetch<GoogleConfig>("/api/v1/auth/google-config");
  }
  return googleConfigCache;
}

export interface DriveConnectResponse {
  /** Picker 렌더용 drive.file access token (단기) */
  access_token: string;
}

export interface DriveConnection {
  connected: boolean;
  folder_name: string | null;
}

/** GIS 코드 클라이언트 code → 백엔드가 토큰 저장 + Picker용 access token 반환 */
export function connectDrive(code: string) {
  return apiFetchAuth<DriveConnectResponse>("/api/v1/auth/drive/connect", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

/** Picker로 선택한 폴더를 감시 대상으로 저장 (연동 완료) */
export function saveDriveFolder(folderId: string, folderName: string | null) {
  return apiFetchAuth<{ status: string; folder_name: string | null }>(
    "/api/v1/takeout/drive/folder",
    {
      method: "POST",
      body: JSON.stringify({ folder_id: folderId, folder_name: folderName }),
    },
  );
}

/** 현재 폴더 연동 상태 */
export function getDriveConnection() {
  return apiFetchAuth<DriveConnection>("/api/v1/takeout/drive/connection");
}
