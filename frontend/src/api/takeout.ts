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

export type DriveFileStatus =
  | "new"
  | "pending"
  | "running"
  | "completed"
  | "failed";

export interface DriveFile {
  id: string;
  name: string | null;
  modified_time: string | null;
  status: DriveFileStatus;
  stage: "indexing" | "indexed" | "profiling" | null;
}

/** 연동 폴더의 Takeout 파일 목록 + 파일별 분석 상태 */
export function listDriveFiles() {
  return apiFetchAuth<{ files: DriveFile[] }>("/api/v1/takeout/drive/files");
}

/** 특정 Drive 파일 분석 트리거 (batchId 있으면 그 배치에 소속) */
export function triggerDriveFile(fileId: string, batchId?: string) {
  const query = batchId ? `?batch_id=${encodeURIComponent(batchId)}` : "";
  return apiFetchAuth<{ status: string; task_id?: string }>(
    `/api/v1/takeout/drive/trigger/${fileId}${query}`,
    { method: "POST" },
  );
}

/** 배치 '다 보냄'(seal) — 업로드/트리거를 모두 보낸 뒤 호출 → 배치 닫고 트리거 */
export function sealBatch(batchId: string) {
  return apiFetchAuth<{ status: string }>(
    `/api/v1/indexer/batch/${batchId}/seal`,
    { method: "POST" },
  );
}

export interface ScheduleInfo {
  connected: boolean;
  folder_name: string | null;
  interval_months: number;
  next_analysis_at: string | null;
}

/** 자동분석 주기 설정 + Drive 연동 상태 조회 */
export function getSchedule() {
  return apiFetchAuth<ScheduleInfo>("/api/v1/takeout/schedule");
}

/** 자동분석 주기(1~12개월) 변경 */
export function updateSchedule(intervalMonths: number) {
  return apiFetchAuth<{ interval_months: number; next_analysis_at: string }>(
    "/api/v1/takeout/schedule",
    { method: "PUT", body: JSON.stringify({ interval_months: intervalMonths }) },
  );
}
