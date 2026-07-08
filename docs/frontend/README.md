# Frontend

Vite + React 19 + React Router 7 SPA. 로그인 후 **`/me` 사용자 허브**를 중심으로 분석·이상향·재생목록·스크랩·트렌드·설정을 제공한다. (과거 에이전트별 페이지 구조에서 재편됨)

```bash
cd frontend && pnpm install && pnpm dev
```

- 패키지 매니저 **pnpm**(npm 금지). 경로 별칭 `@/` → `src/`.
- API 베이스 URL: `VITE_API_BASE_URL` (Docker/nginx `http://localhost`, 로컬 dev `http://localhost:8000`).
- 스택: React 19 · React Router 7 · Vite 8 · TypeScript · Tailwind v4 · Zustand 5 · shadcn/ui(new-york) · recharts · three / react-force-graph(2D·3D) · react-markdown.

## 레이어

```
pages/        URL 진입점 — 라우트 연결, 조합 위주 (얇게)
routes/       router.tsx(createBrowserRouter) + paths.ts(ROUTES 상수)
components/   UI — shell · 도메인별 화면 조각 · shadcn(ui/)
api/          HTTP 클라이언트 + 백엔드 요청/응답 DTO
stores/       Zustand 전역 상태 (여러 화면 공유분만)
features/     도메인 훅 묶음 (features/{domain}/hooks/…)
lib/          env · 유틸 · 도메인 변환·라벨·연동 헬퍼
styles/       globals.css (Tailwind v4 진입)
```

데이터 흐름: `Page → Component → api/(fetch) → useState 또는 stores/` , 표시용 가공은 `lib/{domain}/`.

## 라우트 (`routes/`)

모든 화면은 `ShellLayout` 아래에 중첩된다. path 상수는 `routes/paths.ts::ROUTES`.

| URL | Page | 설명 |
|-----|------|------|
| `/` | `HomePage` | 랜딩 + 큐레이터 챗 데모 |
| `/login` | `LoginPage` | 구글 로그인 |
| `/me` | `MyHubPage` | 사용자 허브(대시보드) |
| `/me/activity` | `MyActivityPage` | 오늘 체류시간·도메인 TOP (익스텐션 tracking) |
| `/me/analyses` | `MyAnalysesPage` | 분석 스냅샷 목록 + 진행 중 job |
| `/me/analyses/compare?from=&to=` | `AnalysisComparePage` | 두 스냅샷 비교 |
| `/me/analyses/:id` | `AnalysisDetailPage` | 스냅샷 단건(21축·portrait·그래프) |
| `/me/ideals` | `IdealManagementPage` | 이상향 목록·적용 |
| `/me/ideals/new` | `IdealSetupPage` | 대화형 이상향 설계(SSE) |
| `/me/ideals/:id` | `IdealDetailPage` | 이상향 상세·비교·가이드·재생목록 진입 |
| `/me/playlists` | `PlaylistPage` | 재생목록 생성·편집·저장 (`?ideal=` 필터) |
| `/trends` | `TrendDetailPage` | 트렌드(Aggregator) |
| `/me/scraps` | `ScrapPage` | 스크랩 목록·그래프 |
| `/me/scraps/:id` | `ScrapDetailPage` | 스크랩 단건 |
| `/settings` | `SettingsPage` | 결제/구독·계정·자동분석 주기·Drive 연동 |
| `/upload` | `UploadPage` | Takeout 업로드·Drive 연동 |
| `/download` | `DownloadPage` | 익스텐션/데이터 안내 |
| `/payment/success` | `PaymentSuccessPage` | 결제 완료 |
| `/agents/:slug` | `AgentDetailPage` | 제네릭 에이전트 소개 |
| `/agents/:slug/posts` · `/agents/:slug/posts/:postId` | `TrendPostsPage` · `TrendPostDetailPage` | 트렌드 포스트 |
| `*` | `NotFoundPage` | |

## 폴더 트리

```
src/
├── main.tsx · App.tsx
├── pages/                    # 위 라우트 표의 화면들 (+ agents/AgentDetailPage, agents/aggregator/Trend*)
├── routes/ router.tsx · paths.ts
├── api/                      # HTTP + DTO
│   ├── client.ts             # 공통 apiFetch / apiFetchAuth (JWT·에러 처리)
│   ├── auth · profiler · analyses · navigator · indexer · takeout
│   ├── curator · archiver · scraps · trend · payment · tracking
│   └── types/ navigator.ts · profiler.ts   # 분량 큰 DTO 분리
├── stores/                   # Zustand
│   ├── auth.ts               # token·user (persist: synapse-auth)
│   ├── shell.ts              # 선택 상태 (persist: synapse-shell)
│   ├── sidebar.ts            # 사이드바 열림/접힘 (persist)
│   ├── chat.ts               # 큐레이터 챗 세션·메시지 (persist)
│   ├── chat-theme.ts         # 챗 테마 프리셋 (persist)
│   ├── theme.ts              # 라이트/다크 테마
│   └── scrap-detail-panel.ts # 스크랩 상세 패널 열림 상태
├── features/
│   └── scraps/hooks/useScrapDetail.ts
├── components/
│   ├── ui/                   # shadcn 공통
│   ├── shell/                # ShellLayout · Sidebar · AccountSidePanel
│   ├── home/                 # 랜딩·큐레이터 챗·그래프 데모 (chat-messages, curator-input, *-graph 등)
│   ├── analyses/             # 프로필 차트 (axis-radar, behavior-spider-chart, interest-pie, embedding-catalog-graph[-3d] 등)
│   ├── ideals/               # CompareBars · RadarCompareChart
│   ├── scraps/               # 스크랩 패널·임베딩 그래프
│   ├── aggregator/           # 트렌드 대시보드·그래프
│   ├── auth/                 # 로그인·프로필 편집 모달
│   ├── upload/               # upload-panel (Takeout·Drive)
│   ├── agent-card.tsx · agent-detail.tsx
├── lib/
│   ├── utils.ts(cn) · env.ts · agents.ts
│   ├── auth-protocol.ts · extension-auth-sync.ts   # 익스텐션 인증 연동 (shared/auth-protocol.ts 규약)
│   ├── google-picker.ts · youtube-connect.ts       # Drive Picker · YouTube 연동
│   ├── youtube-categories.ts · upload-local-storage.ts
│   └── analyses/ · navigator/ · scraps/ · trends/ · sidebar/   # 도메인 변환·라벨
└── styles/globals.css
```

## 배치 규칙

| 추가하는 것 | 위치 |
|-------------|------|
| 새 URL 화면 | `pages/` + `routes/paths.ts` + `router.tsx` |
| 새 API 엔드포인트 | `api/{domain}.ts` (큰 DTO는 `api/types/{domain}.ts`) |
| 여러 화면 공유 클라이언트 상태 | `stores/` (필요 시 `persist`) |
| 한 화면만의 상태 | 컴포넌트 `useState` |
| 도메인 훅 묶음 | `features/{domain}/hooks/` |
| 차트·표 데이터 변환·라벨 | `lib/{domain}/` |
| 도메인 UI 조각 | `components/{domain}/` |
| shadcn 공통 UI | `components/ui/` (`npx shadcn@latest add`) |

- **api/ vs lib/**: `api/`는 "서버가 준 그대로"(DTO·fetch), `lib/`는 "화면에 맞게 가공·표시".
- 익스텐션과의 인증 규약은 `shared/auth-protocol.ts`를 공유(`lib/auth-protocol.ts`·`extension-auth-sync.ts`).
- 빌드 산출물 `frontend/dist/`. `pnpm build`가 곧 타입체크(PR 전 통과 필수).
