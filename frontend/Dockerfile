# Synapse Frontend 이미지 (nginx + 빌드된 SPA + 리버스프록시 + HTTPS)
#
# ⚠️ 빌드 컨텍스트는 레포 루트(.)다.
#    frontend가 @synapse/shared(../shared)를 참조하기 때문.
#    빌드 예: docker build -f frontend/Dockerfile -t synapse-frontend .

# ── Stage 1: 프론트 빌드 ──────────────────────────────
FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@11.5.2 --activate

WORKDIR /app

# 의존성 먼저 (캐시 활용)
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./frontend/
WORKDIR /app/frontend
RUN pnpm install --frozen-lockfile

# 소스 복사 (shared 포함)
WORKDIR /app
COPY shared ./shared
COPY frontend ./frontend

# 운영 API 주소 주입 (공개값 — 시크릿 아님)
ARG VITE_API_BASE_URL=https://ifive.site
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

WORKDIR /app/frontend
RUN pnpm run build

# ── Stage 2: nginx 서빙 ───────────────────────────────
FROM nginx:1.27-alpine

# 빌드된 정적 파일
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
# nginx 설정 (HTTP→HTTPS, /api 프록시, SSL)
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
