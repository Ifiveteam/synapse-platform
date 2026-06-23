# 배포 계획 — GitHub Actions → Docker Hub → 단일 EC2

> 대상: frontend + backend + db (extension 제외 — 크롬 웹스토어 별도 트랙).
> 흐름: push → GH Actions가 이미지 빌드 → Docker Hub push → EC2가 pull → compose up.

## 1. 이미지 전략 (2개 커스텀 + 1개 공식)

| 이미지 | 내용 | 용도 |
|--------|------|------|
| `user/synapse-backend:<tag>` | FastAPI (기존 backend/Dockerfile) | `migrate` + `backend` 둘 다 |
| `user/synapse-frontend:<tag>` | **nginx + 빌드된 dist + nginx.conf** (단일 웹 진입) | 80/443, `/api`→backend 프록시 |
| `pgvector/pgvector:pg17` | 공식 | db (push 불필요) |

- **태그**: git SHA(`:sha-xxxx`) + `:latest`. EC2 compose는 태그 핀(롤백은 이전 태그로).
- 현재 frontend Dockerfile은 **builder 단계만** 있음 → **nginx 서빙 단계 추가**해서 한 이미지로 굽는다
  (지금의 "dist 볼륨 복사 + 별도 nginx 서비스" 패턴 폐기 → 푸시 가능한 단일 이미지).

## 2. 레포에 추가할 것

1. **`frontend/Dockerfile`** 2차 스테이지 추가:
   `FROM nginx:1.25-alpine` → builder의 `/app/dist` 복사 + `nginx/nginx.conf` 복사.
   (단일 origin: `VITE_API_BASE_URL`=prod 도메인, `/api`는 nginx가 backend로 프록시 → CORS 회피)
2. **`compose.prod.yml`** (EC2용, `build:` 대신 `image:`):
   - `db`: pgvector, **published 5432 제거**, 데이터는 EBS 볼륨.
   - `migrate`: backend 이미지로 `alembic upgrade head` (db healthy 후).
   - `backend`: backend 이미지, `env_file: .env`, 포트 미공개(내부만), migrate 완료 후.
   - `web`(frontend): frontend 이미지, **80/443**, backend 의존, TLS 인증서 마운트.
3. **`.github/workflows/deploy.yml`** (아래 4·5).
4. **EC2의 `.env`** (런타임 시크릿, git 미포함).

## 3. CI — 빌드 & 푸시 (push to main 또는 release 태그)

```
job build-push:
  - checkout
  - docker/login-action (DOCKERHUB_USERNAME/TOKEN)
  - buildx: backend 이미지 build+push (:sha, :latest)
  - buildx: frontend 이미지 build+push
      build-args: VITE_API_BASE_URL=https://<도메인>
```

## 4. CD — EC2 배포 (build-push 성공 후)

```
job deploy (needs build-push):
  - appleboy/ssh-action 로 EC2 접속 (EC2_HOST, EC2_SSH_KEY)
  - 원격에서:
      docker login
      docker compose -f compose.prod.yml pull
      docker compose -f compose.prod.yml up -d   # migrate→backend→web 순서
      docker image prune -f
```
- `migrate` 서비스가 매 배포마다 `alembic upgrade head` 자동 실행 (신규 리비전 반영).
- compose.prod.yml은 EC2에 미리 둠(또는 CD가 scp). `.env`도 EC2에 상주.

## 5. 시크릿 분리

- **GitHub Actions secrets**: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `EC2_HOST`, `EC2_SSH_KEY`, (빌드용 `VITE_API_BASE_URL`).
- **EC2 `.env`** (런타임, git X): `DATABASE_URL`, `GOOGLE_CLIENT_ID/SECRET`, `OPENAI_API_KEY`,
  `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `YOUTUBE_API_KEY`, `FRONTEND_BASE_URL`, `RESEND_*`, `NAVER_*`.

## 6. EC2 1회 셋업

1. 인스턴스 **t3.small~medium↑**(umap/ML·프로파일러 메모리), EBS 추가 볼륨(pgdata).
2. docker + compose plugin 설치.
3. `/opt/synapse`에 `compose.prod.yml` + `.env` 배치.
4. 도메인 A레코드 → EC2 IP. **TLS** (택1):
   - Caddy 앞단(자동 Let's Encrypt, 설정 최소) ← 추천
   - 또는 nginx+certbot
   - 또는 ALB+ACM(인스턴스 TLS 불필요, 비용↑)
5. **Google OAuth 콘솔**: redirect URI `https://<도메인>/api/v1/auth/callback` 등록.
6. **보안그룹**: 80/443 오픈, 22는 내 IP만, **5432/8000은 미오픈**.

## 7. 이 스택 특화 주의

- **VITE_API_BASE_URL은 빌드타임 고정** → frontend 이미지는 환경 종속(도메인 바뀌면 재빌드).
  같은 origin(`/api` 프록시) 전제로 prod 도메인 1개만 쓰면 단순.
- **db published 포트 제거 필수**(현 compose는 5432 노출 — prod에선 닫기). 데이터는 **EBS + 스냅샷/pg_dump**.
- **backend 단일 uvicorn 워커, `--reload` 금지**(Dockerfile은 이미 OK). 인메모리 잡이 프로세스별이라 멀티워커 X.
- **migrate 순서 보장**(depends_on completed_successfully) — 첫 배포 시 스키마 생성, 이후 신규 리비전 적용.
- **SSE OK**: nginx.conf가 `proxy_buffering off` + 300s timeout이라 챗 스트리밍 정상.
- **롤백**: 이전 이미지 태그로 `up -d`.
- 작은 인스턴스에서 빌드 OOM 위험 → **빌드는 GH Actions(러너)에서**, EC2는 pull만 (이 구조가 그걸 해결).

## 8. 단계별 진행 순서 (추천)

1. frontend Dockerfile nginx 스테이지 추가 + `compose.prod.yml` 작성
2. Docker Hub 리포 생성 + GH secrets 등록
3. `deploy.yml` 작성 (build-push → deploy)
4. EC2 셋업(도커·EBS·.env·도메인·TLS·OAuth)
5. main push로 첫 배포 → 헬스/로그 확인 → OAuth 로그인 E2E

## 다음 단계 (이 계획 밖)
- extension: `VITE_API_URL`=prod, manifest host_permissions/authBridge origin에 prod 도메인, 백엔드 익스텐션 redirect 허용 → 웹스토어 게시.
- 추후 확장: db→RDS(pgvector), 정적→S3+CloudFront, 잡큐 재도입 시 워커 분리.
