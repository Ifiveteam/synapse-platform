/** Backend API base URL — client·auth 서비스 등 공통 import (순환 의존 방지). */
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
