# Frontend 개요

Vite + React 19 SPA의 `frontend/src/` 폴더 역할과 코드 배치 규칙.

- 디렉터리 트리·라우트·스택: [FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md)
- 실행: `cd frontend && pnpm install && pnpm dev`
- API 베이스 URL: `VITE_API_BASE_URL` (Docker/nginx `http://localhost`, 로컬 dev `http://localhost:8000`)

## 레이어 요약

```
pages/        URL 진입점 — 라우트와 연결, 레이아웃·조합만 (얇게)
routes/       React Router 설정, path 상수
components/   UI — shell, 에이전트별 화면, shadcn
api/          HTTP 클라이언트 + 백엔드 응답/요청 DTO
stores/       Zustand 전역 상태 (여러 화면에서 공유하는 것만)
lib/          env, 유틸, 에이전트 메타, 도메인 변환·라벨·mock
hooks/        앱 전역 공통 훅 (필요 시)
styles/       전역 CSS
```

데이터 흐름은 대체로 다음과 같다.

```
Page → Component → api/ (fetch) → setState 또는 stores/
                         ↓
                    lib/ (가공·표시용 변환)
```

## 폴더별 설명

### `pages/`

라우터가 직접 렌더하는 **화면 진입점**. 비즈니스·UI 대부분은 `components/`에 두고, 페이지는 조합만 한다.

- 공통: `HomePage`, `LoginPage`, `SetupPage`, `NotFoundPage`
- 에이전트: `pages/agents/` — Profiler, Navigator, Indexer, Aggregator(트렌드) 등

### `routes/`

- `router.tsx` — `createBrowserRouter` 등 라우트 정의
- `paths.ts` — `ROUTES` 상수 (`/agents/profiler` 등). 하드코딩 URL 대신 여기서 import

### `components/`

재사용 UI와 에이전트별 화면 조각.

| 하위 | 역할 |
|------|------|
| `ui/` | shadcn 기반 공통 컴포넌트 (Button, Badge 등) |
| `shell/` | `ShellLayout`, `Sidebar` — 로그인 후 공통 레이아웃 |
| `profiler/`, `navigator/`, `aggregator/` | 에이전트 전용 UI |
| 루트 | `agent-card.tsx`, `agent-detail.tsx` 등 홈·에이전트 공통 |

에이전트 페이지의 복잡한 로직·폼·탭 상태는 **컴포넌트 안 `useState`** 또는 **커스텀 훅**으로 둔다. 별도 `handlers/`, `services/` 레이어는 없다.

### `api/`

**HTTP만** 담당. 백엔드와 주고받는 JSON 형태(계약)와 fetch 함수.

| 파일 | 내용 |
|------|------|
| `client.ts` | 공통 `apiFetch` (인증 헤더, 에러 처리) |
| `auth.ts` | `/api/v1/auth` |
| `profiler.ts` | Profiler API 호출 |
| `trend.ts` | Aggregator 트렌드 API 호출 + DTO (인라인) |
| `types/profiler.ts` | Profiler 응답/요청 DTO (분량이 커서 파일 분리) |

**타입 배치 규칙**

- 백엔드 스키마와 1:1인 DTO → `api/` (작으면 `api/trend.ts`처럼 같은 파일, 크면 `api/types/{domain}.ts`)
- UI 전용·뷰 모델·라벨 상수 → `lib/{domain}/`
- 컴포넌트만 쓰는 props/state → 해당 컴포넌트 근처

DTO 타입은 `api/`에 두어도 `stores/`, `components/`, `lib/`에서 import할 수 있다. 서버에서 내려온 데이터 모델이기 때문이다.

**예외:** Navigator는 `lib/navigator/api.ts` + `lib/navigator/types.ts`로 묶여 있다. 도메인 타입에 UI 상수(`AXIS_LABELS` 등)가 많아 `lib/`에 둔 형태이며, Profiler API 타입(`ProfilerResult`)은 `@/api/types/profiler`를 참조한다.

### `stores/`

[Zustand](https://github.com/pmndrs/zustand) **전역 상태**. API 호출은 하지 않고, setter로 값만 갱신한다.

| 스토어 | 상태 | 비고 |
|--------|------|------|
| `auth.ts` | `token`, `user` | `persist` — localStorage `synapse-auth` |
| `shell.ts` | `selectedAgentId` | 사이드바·에이전트 카드 선택 |
| `profiler.ts` | `result` (`ProfilerResult`) | Navigator 등 다른 에이전트에서 프로필 재사용 |

페이지·폼·로딩·탭처럼 **한 화면 안에서만 쓰는 상태**는 store에 올리지 않는다. Trend, Indexer 등은 전용 store가 없고 컴포넌트 로컬 state를 쓴다.

### `lib/`

프레임워크에 덜 묶인 **공통·도메인 로직**.

| 경로 | 역할 |
|------|------|
| `env.ts` | `VITE_*` 환경 변수 |
| `utils.ts` | `cn()` 등 범용 유틸 |
| `agents.ts` | 에이전트 메타 (`AGENTS`, `AgentId`) |
| `profiler/` | 그래프 데이터 변환, 축 라벨 등 |
| `navigator/` | Navigator API·타입·mock |

`api/`와 구분: `api/`는 “서버가 준 그대로”, `lib/`는 “화면에 맞게 가공·표시”.

### `hooks/`

여러 페이지/컴포넌트에서 같이 쓰는 훅을 둘 자리. 현재는 비어 있어도 된다 (`.gitkeep`).

### `styles/`

`globals.css` — Tailwind v4 진입, 전역 스타일.

## 경로 별칭

`@/` → `src/` (`tsconfig.json`, `vite.config.ts`). import 예: `@/api/profiler`, `@/stores/auth`.

## 빌드 산출물

- Vite 빌드 결과: `frontend/dist/`
- 예전 Next.js 캐시 `.next/`는 사용하지 않음 (삭제해도 됨)

## 새 코드 넣을 때

| 추가하는 것 | 넣을 위치 |
|-------------|-----------|
| 새 URL 화면 | `pages/` + `routes/` |
| 새 API 엔드포인트 | `api/{domain}.ts` 또는 `api/types/` |
| 여러 화면에서 쓰는 클라이언트 상태 | `stores/` |
| 한 컴포넌트/페이지만의 상태 | 해당 파일 `useState` |
| 차트·테이블용 데이터 변환 | `lib/{domain}/` |
| 에이전트 전용 UI | `components/{agent}/` |
| shadcn 공통 UI | `components/ui/` |

## 관련 문서

- [FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md) — 전체 트리, 라우트 표, 스택 버전
