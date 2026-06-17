const DEFAULT_API_BASE_URL = "http://localhost:8000";

/** 로컬 dev 기본값 — .env 없어도 docker-compose 백엔드(8000)로 연결 */
export const API_BASE_URL = (() => {
  const fromEnv = import.meta.env.VITE_API_BASE_URL?.trim();
  return fromEnv || DEFAULT_API_BASE_URL;
})();

export const TREND_API_BASE = `${API_BASE_URL}/api/v1/trend`;
