# Synapse Platform Frontend
#  - builder  : Vite 빌드 (dist 생성).
#  - runtime  : nginx + dist + nginx.conf 단일 이미지 (배포용, /api→backend 프록시).
#
# ⚠ 빌드 컨텍스트는 "리포 루트" 여야 함 (frontend/ + 형제 shared/ 둘 다 필요).
#   tsconfig/vite 의 "@synapse/shared" → ../shared 별칭 때문.
#     docker build -f frontend/Dockerfile -t synapse-frontend .

FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@11.5.2 --activate

WORKDIR /app/frontend

# 1) 의존성만 먼저 (캐시 레이어)
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# 2) 형제 shared 패키지 (../shared 별칭 대응) + 프론트 소스
COPY shared /app/shared
COPY frontend ./

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN pnpm run build

# ── 배포용 서빙 스테이지 ──────────────────────────────────
FROM nginx:1.25-alpine AS runtime

# SPA 정적 파일 + 단일 진입점 nginx 설정 (/, /api→backend, SSE 대응)
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
