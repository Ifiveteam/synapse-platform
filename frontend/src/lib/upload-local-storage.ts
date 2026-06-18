/**
 * localStorage 항목 이름 (API 비밀키·인증 토큰 아님).
 * 업로드/Drive 분석 UI를 새로고침 후에도 이어가기 위한 브라우저 저장소 라벨.
 */
export const uploadLocalStorage = {
  directUploadTask: "synapse-upload-task",
  driveTasks: "synapse-drive-tasks",
  driveAnalyzed: "synapse-analyzed-files",
  /** 예전 버전 잔여 데이터 삭제용 */
  driveStatsLegacy: "synapse-drive-stats",
} as const;
