# Frontend 폴더 구조

Vite + React 19 + React Router SPA. 폴더 역할·규칙: [OVERVIEW.md](./OVERVIEW.md)

```bash
cd frontend && pnpm install && pnpm dev
```

환경 변수: `VITE_API_BASE_URL` (Docker/nginx: `http://localhost`, 로컬 dev: `http://localhost:8000`)

## 디렉터리

```
frontend/
├── index.html
├── vite.config.ts
├── package.json
└── src/
    ├── main.tsx
    ├── App.tsx
    │
    ├── pages/                    # URL 진입점
    │   ├── HomePage.tsx
    │   ├── LoginPage.tsx
    │   ├── SetupPage.tsx
    │   ├── NotFoundPage.tsx
    │   └── agents/
    │       ├── ProfilerPage.tsx
    │       ├── NavigatorPage.tsx
    │       ├── IndexerPage.tsx
    │       ├── AgentDetailPage.tsx
    │       └── aggregator/
    │           ├── TrendPostsPage.tsx
    │           └── TrendPostDetailPage.tsx
    │
    ├── routes/                   # 라우터, path 상수
    │   ├── router.tsx
    │   └── paths.ts
    │
    ├── api/                      # HTTP
    │   ├── client.ts
    │   ├── auth.ts
    │   ├── profiler.ts
    │   ├── trend.ts
    │   └── types/
    │       └── profiler.ts
    │
    ├── stores/                   # Zustand
    │   ├── auth.ts
    │   ├── shell.ts
    │   └── profiler.ts
    │
    ├── components/
    │   ├── ui/                   # shadcn
    │   ├── shell/                # ShellLayout, Sidebar
    │   ├── profiler/
    │   ├── navigator/
    │   ├── aggregator/
    │   ├── agent-card.tsx
    │   └── agent-detail.tsx
    │
    ├── hooks/                    # 공통 훅 (필요 시)
    ├── lib/                      # utils, env, agents 메타
    │   ├── utils.ts
    │   ├── env.ts
    │   ├── agents.ts
    │   ├── profiler/
    │   └── navigator/
    │
    └── styles/
        └── globals.css
```

## 라우트

| URL | Page |
|-----|------|
| `/` | HomePage |
| `/login` | LoginPage |
| `/setup` | SetupPage |
| `/agents/profiler` | ProfilerPage |
| `/agents/navigator` | NavigatorPage |
| `/agents/indexer` | IndexerPage |
| `/agents/:slug` | AgentDetailPage |
| `/agents/aggregator/posts` | TrendPostsPage |
| `/agents/aggregator/posts/:postId` | TrendPostDetailPage |

## 스택

- Vite 8, React 19, React Router 7, TypeScript, Tailwind v4, Zustand, pnpm
- Node `^20.19.0` 또는 `>=22.12.0`
