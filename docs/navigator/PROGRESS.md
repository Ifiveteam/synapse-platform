# Navigator 구현 현황

> 계획: [PLAN.md](./PLAN.md) · 갱신: 2026-06-22

## 요약 (한눈에)

| 영역 | 상태 |
|------|------|
| 백엔드 코드 (6 엔드포인트 + 3계층 + 파사드) | ✅ 완료 |
| 구조 정리 (파사드 `base.py`, `tool.py`→`ideal.py`/`guide.py`, `tools/` 예약) | ✅ 완료 |
| 정적 검증 (ruff·compile·import·라우트) | ✅ 통과 |
| **에이전트 스모크 (실제 Gemini)** | ✅ 통과 |
| HTTP 전체 E2E (DB·인증·영속) | ✅ 통과 (dev-login→proposals→create→apply→list→comparison→guide→chat SSE) |
| **프론트엔드 연결** (새 8축/실 API) | ✅ 완료 (tsc 통과) |
| 가이드 RAG 실 catalog 데이터 검증 | ⬜ 이후 (현재 fallback 경로만 확인) |
| 익스텐션 YouTube 조작·재생목록 | ⬜ 이후 |

**다음 작업 = 브라우저 동작 확인 (사장님이 직접) → 이후 익스텐션.**

### 프론트엔드 연결 (실 API) ✅
- [x] `api/auth.ts` `devLogin()` + `stores/auth.ts` `loginDev()` + `login-panel.tsx` 게스트→loginDev
- [x] `lib/ideals/api.ts` — 실 REST(getProposals/createIdeal/listIdeals/getIdeal/applyIdeal/getComparison/getGuide/getCurrentAxes) + `streamChat` SSE 파서
- [x] `stores/sidebar.ts` `activeIdealLabel` + `Sidebar.tsx` 적용중 이상향 표기
- [x] `IdealManagementPage.tsx` — listIdeals/applyIdeal + 사이드바 동기화 (확정/설정 탭, 새로추가)
- [x] `IdealDetailPage.tsx` — getIdeal+getComparison(병렬)+getGuide(별도) 레이더·gap·가이드·적용
- [x] `IdealSetupPage.tsx` — Step1 분석선택(목) → Step2 getProposals+getCurrentAxes 펼침카드 → 확정(createIdeal) / 채팅 세부조정(streamChat→CUSTOM 확정)

## 완료 ✅

### DB / 모델
- [x] `models/user_ideal_persona.py` — `source_profile_history_id`(UUID FK→`user_profile_history.id`, SET NULL) 컬럼 추가
- [x] `alembic/versions/007_navigator_ideal_source.py` — 컬럼 추가 마이그레이션 (down_revision=`006_extension_auth`)

### 에이전트 (`agents/navigator/`)
- [x] `constants.py` — BEHAVIOR_AXES(8) SSOT, GEMINI_MODEL, NAVIGATOR_AGENT_TYPE, temps, STREAM_ERROR_*
- [x] `schemas.py` — IdealType, IdealRadar, IdealAdjustment, AxisGap, RadarComparison, GuideStep/Guide, NavigatorStreamEvent
- [x] `state/navigator.py` — NavigatorState (TypedDict, messages=add_messages)
- [x] `ideal.py` — extract_8axis, clamp, propose_ideals(반대·강점심화·균형 3종), compare(순수)
- [x] `guide.py` — generate_guide
- [x] `tools/` — (예약) LLM function-calling 도구 모음 전용 (코드가 부르는 기능과 분리)
- [x] `gemini.py` — Gemini 클라이언트 (invoke_structured/_safe)
- [x] `streaming.py` — SSE envelope (event:/data:{"content"}), event=status|token|ideal
- [x] `prompts/` — propose.py / chat.py / guide.py / __init__(render 헬퍼)
- [x] `nodes/` — _common.py / interpret.py(structured 조정 + status·ideal 이벤트) / respond.py(토큰 스트리밍)
- [x] `graph.py` — build_navigator_graph()(StateGraph 빌드·컴파일)
- [x] `base.py` — **NavigatorAgent 파사드** (propose/compare/generate_guide/normalize_ideal/current_axes/chat_stream), get_navigator_agent 싱글톤. service는 이 파사드만 호출(tool·graph 직접 import 없음)
- [x] `sub_agent/__init__.py` — 다음 단계 placeholder

### 레이어 (service / repository / schema / api)
- [x] `repositories/navigator_repository.py` — user_ideal_persona upsert/get + AIChatLog(NAVIGATOR) CRUD + encode/decode_description
- [x] `services/navigator/service.py` (+`__init__.py` 재노출) — **글루 전용**(NavigatorAgent 파사드 주입). get_proposals / stream_chat(SSE) / confirm_ideal / get_ideal / get_comparison / get_guide + `_load_profile_or_404`
- [x] `schemas/navigator.py` — HTTP DTO (AxisScores8, Proposals/Ideal/Comparison/Guide 등)
- [x] `api/v1/navigator.py` — 6개 엔드포인트 (모두 `get_current_user_dep`)
- [x] `api/v1/__init__.py` — navigator_router 재등록

### 검증 통과
- [x] `uv run ruff check ...` — All checks passed
- [x] `uv run python -m compileall app` — exit 0
- [x] `build_navigator_graph()` — graph ok
- [x] `from app.api.v1 import api_router` — `/api/v1/navigator/{proposals,chat/stream,ideal,comparison,guide}` 6개 등록
- [x] `import app.main` — ok

## 미완료 / 다음 작업 ⬜

### 가이드 그라운딩 서브에이전트 ✅ (catalog RAG)
- [x] `agents/navigator/sub_agent/guide/` — retrieve→generate→evaluate 자율 루프(프렉탈 graph)
  - `store.py`(CatalogStore Port+CatalogHit), `state.py`, `constants.py`(축 검색문구·한도), `prompts.py`(그라운딩+폴백), `nodes/{retrieve,generate,evaluate}.py`, `graph.py`(run_guide)
  - retrieve: 약한축(gap>0 top3) 임베딩→`store.search_by_axis`(pgvector cosine) 근거 검색
  - evaluate(규칙): 근거 부족→재검색(완화) / 커버 부족→재생성 / 충분→done (한도 2)
  - 폴백: store·embedding·catalog 없으면 일반 가이드
- [x] `navigator_repository.search_by_axis` — `user_watch_catalog.embedding` cosine 검색 (CatalogStore 구현)
- [x] `base.generate_guide(store, user_id, …)` → 서브에이전트 위임 / `service.get_guide`가 `store=self.repo` 주입
- [x] 옛 `guide.py`·`prompts/guide.py` → 서브에이전트로 흡수·삭제

### 에이전트 스모크 (실제 Gemini) ✅ 통과
- [x] `scripts/navigator_smoke.py` — DB 없이 propose(3종)→compare→guide(서브에이전트)→chat 실제 Gemini 호출 성공
  - 3 아키타입 차별화, 챗 interpret 조정 + SSE(status/ideal/token) 정상
  - **가이드: 약한축 top3 정확 선정 + 가짜 store 그라운딩 / store=None 폴백** 둘 다 확인
  - 실행: `cd backend && PYTHONUTF8=1 PYTHONPATH=. uv run python scripts/navigator_smoke.py`

### HTTP 전체 E2E ✅ 통과 (실제 서버, 2026-06-22)
- 환경: `docker compose -f docker-compose.dev.yml up`(db+migrate[007]+backend :8000), seed 없이 `POST /profiler/run`(빈 catalog→rule fallback)로 프로필 생성
- [x] `POST /auth/dev-login` → 토큰
- [x] `POST /profiler/run` → `user_profile_history` 생성
- [x] `GET /proposals` → 3종(실제 Gemini)
- [x] `POST /ideal` → 저장 (`source_profile_history_id` 반영) / `GET /comparison` → gap
- [x] `GET /guide` → 약한 축 정확 타깃 (catalog 없어 **그라운딩은 폴백**)
- [x] `POST /chat/stream` → SSE(status/ideal/token), interpret 조정 + respond 스트리밍
- 주의: 한글 JSON 본문은 Windows .exe 인자로 깨짐 → **파일(`--data-binary @file`)** 로 전송

### 다개 이상향 + 적용(1개) ✅ (마이그레이션 008, HTTP E2E 통과)
- 요구사항: **이상향 여러 개 생성·보관, 그중 1개만 "적용 중"**
- 모델: `user_ideal_persona` + `is_active` (008), 유저당 여러 행
- repo: `create_ideal`(insert)/`list_ideals`/`get_ideal(id)`/`get_active_ideal`/`set_active`(1개만 active)
- API: `POST /ideal`(생성) · `GET /ideals` · `GET /ideal/{id}` · `POST /ideal/{id}/apply` · `GET /ideal/{id}/comparison` · `GET /ideal/{id}/guide`
- E2E 통과: 생성→apply→목록(1개만 active)→comparison→guide

### 남은 검증
- [ ] **가이드 RAG 그라운딩 실검증** — `user_watch_catalog`+embedding 있는 유저로 `GET /ideal/{id}/guide`가 진짜 시청 영상 근거를 무는지 (현재 catalog 없어 폴백)
- [ ] (선택) `ideal.compare`/`clamp` 단위 테스트

## 🔜 다음: 프론트 ↔ 백엔드 연결
- `lib/navigator/api.ts`·`types.ts` 새 엔드포인트+JWT(apiFetchAuth)로 재작성
- dev-login으로 실 토큰 확보 (지금 프론트는 mock 토큰)
- 화면 연결: 설정(proposals/chat/생성) · 목록/적용(`/ideals`,`/apply`) · 상세(`/ideal/{id}/comparison`,`/guide`)

### 이후 단계 (프론트 다음)
- [ ] 익스텐션 YouTube 조작(하이브리드: 시청=DOM 자동화 / 재생목록·구독=Data API + OAuth `youtube` 스코프)
- [ ] `agents/navigator/sub_agent/youtube/` 서브에이전트 + `tools/` LLM 도구 구현

---

## 🖥️ 프론트엔드 재구현 계획 (다음 작업)

> 현재 프론트 navigator는 **옛(삭제된) 백엔드용** — 옛 8축·옛 엔드포인트(`/navigator/design`·`/confirm`…)라 새 API와 불일치. 새 API(새 8축 + `/proposals`·`/chat/stream`·`/ideal`·`/comparison`·`/guide`, **JWT 필수**)에 맞게 재구현 필요.

### 핵심 변화
- 프론트가 **`profiler_data`를 더 이상 안 보냄** — 백엔드가 JWT로 DB 프로필을 읽음. (프로필 없으면 404)
- 모든 호출에 **Bearer JWT** 필요 → `@/api/client`의 **`apiFetchAuth`** 사용 (옛 navigator는 자체 무인증 `apiFetch` 썼음)
- SSE는 **named event**(`status`/`token`/`ideal`) 파싱 필요 (옛것은 `data:`만 + `[DONE]`/`[ERROR]`)

### ♻️ 재사용 (축/타입만 교체)
- `components/navigator/radar-chart.tsx` — SVG 8각 레이더, **렌더 로직 축 무관** → `AXES`/라벨만 새 8축으로. **비교 화면(current vs ideal) 주력 자산**
- `components/navigator/ideal-selector.tsx` — 3종 카드 + gap 배지 + 오버레이 레이더 → 새 `IdealType`(대문자)·새 축·`/comparison` gaps로 매핑
- `apiFetchAuth`(`api/client.ts`), `env.ts`(API_BASE_URL), 라우트(`paths.ts`/`router.tsx`)

### ✏️ 재작성
- `lib/navigator/types.ts` — **새 8축**(exploration…sensitivity), `IdealType` 대문자(`OPPOSITE`/`DEEPEN`/`BALANCE`), 새 `Guide`(`{summary, steps:[{axis,label_ko,title,detail,priority}]}`). **Layer B·Quest·ProfilerData 삭제**
- `lib/navigator/api.ts` — `apiFetchAuth`로 전환 + 새 엔드포인트(`getProposals`/`getIdeal`/`saveIdeal`/`getComparison`/`getGuide`/`streamChat`). `profiler_data`·`user_id`·`top5` 제거
- `pages/agents/NavigatorPage.tsx` — profiler store·Layer B·quest·confirm 제거 → `proposals → 선택/챗(SSE) → /ideal 저장 → /comparison + /guide 한 페이지`
- `lib/navigator/mock.ts` — 재작성 또는 제거

### 🗑️ 삭제 (obsolete)
- `components/navigator/layer-b-gauge.tsx` (새 navigator엔 Layer B 없음)
- `quest-card.tsx`의 `QuestCard` (Quest 없음; `GuideRoadmap`은 새 Guide 구조로 재작성)
- 옛 api 함수: `confirmIdeal`/`modifyDirect`/`modifyByChat`/`optimizeAuto`/`toProfilerData`
- NavigatorPage의 `useProfilerStore` 의존 (store 자체는 프로파일러용으로 유지)

### ⚠️ 주의 (외부 의존 깨짐 방지)
- `lib/navigator/types`의 `IdealType`·`IDEAL_META`를 **`stores/sidebar.ts`·`components/shell/Sidebar.tsx`·`lib/sidebar/mock.ts`가 import** → export 유지 필수
- `IdealType` 소문자→대문자 변경 시: `lib/sidebar/mock.ts`의 `"expansion"` 리터럴 수정 + `Sidebar.tsx`에 `IDEAL_META[type]?.label` 폴백(기존 localStorage `synapse-sidebar` 값이 옛 소문자)

### SSE 패턴 (새로 작성)
```
fetch POST /api/v1/navigator/chat/stream
  headers: Authorization Bearer + Accept text/event-stream
  body: { message, session_id?, working_ideal?, ideal_type? }
→ res.body.getReader() + TextDecoder, 라인 버퍼링
→ event: 줄 추적(status/token/ideal) + data: JSON {content} 파싱
   (ideal 이벤트의 content는 8축 JSON → 레이더 동기화)
```

### 화면 흐름 (목표)
```
① /proposals → 3종 카드(차트+설명)
② 카드 클릭 → [확정] POST /ideal  또는  [채팅조정] POST /chat/stream(SSE)
③ 확정 후 한 페이지: GET /comparison(현재 vs 이상향 레이더) + GET /guide(행동 단계)
```
(프로필 없으면 `/proposals` 404 → "프로파일러 먼저 실행" 안내 처리)

## API 빠른 참조

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/navigator/proposals` | 21축 → 반대·강점심화·균형 이상향 3종 (`proposals[]`) |
| POST | `/api/v1/navigator/chat/stream` | 대화형 이상향 설계 (SSE: status/token/ideal) |
| POST | `/api/v1/navigator/ideal` | 이상향 확정 저장 |
| GET | `/api/v1/navigator/ideal` | 저장된 이상향 조회 |
| GET | `/api/v1/navigator/comparison` | 현재 vs 이상향 gap |
| GET | `/api/v1/navigator/guide` | 행동 가이드 |

## 알려진 제약 / 메모
- `python` 직접 호출은 이 환경에서 깨짐(스토어 스텁) → **모든 명령은 `uv run`** 사용.
- 챗 SSE는 `event: ideal`로 갱신된 8축 JSON을 보내 클라 레이더 동기화. token만 DB 저장(❌ 접두 오류 토큰 제외).
- 네비게이터 채팅 로그는 `ai_chat_logs`(agent_type=`NAVIGATOR`) 재사용, RAG 미사용이라 `content_embedding`=NULL.
- LLM = Gemini(`gemini-2.5-flash`). `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` 필요.
