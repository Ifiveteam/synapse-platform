# ── Stage 1: 의존성 설치 ─────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# package.json만 먼저 복사 (캐시 최적화)
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

# ── Stage 2: 빌드 ────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 환경변수 (빌드 타임)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── Stage 3: 실행 ────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# 비root 유저 (보안)
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Next.js standalone 출력 복사
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
