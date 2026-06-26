# Navigator 전체 계획 & 구현 현황

> 갱신: 2026-06-25. YouTube 재생목록 기능은 별도 문서 [PLAN_youtube_playlist.md](./PLAN_youtube_playlist.md).
> 이 문서 = 네비게이터 전체 설계·결정·현황(과거 PLAN/21axis/proposal_cache/PROGRESS 통합).

## 1. 제품 플로우

1. 프로파일러 **21축 프로필**(가치관10+기질3 = 13축, 행동 8축)을 입력으로
2. **반대 / 강점심화 / 균형** 이상향 3종을 자동 제안 (제안 캐시로 같은 스냅샷=같은 3안 고정)
3. **챗봇 대화(SSE)** 로 이상향을 설계·조율
4. **현재 vs 이상향** 비교(gap)
5. 이상향 기반 **행동 가이드** 생성 (시청기록 RAG 그라운딩)
6. (다음) **YouTube 재생목록 자동생성** → [PLAN_youtube_playlist.md](./PLAN_youtube_playlist.md), **익스텐션 DOM 자동화 시청**

## 2. 아키텍처

**Archiver 패턴 미러링** — stateless LangGraph + service(영속) + repository(asyncpg) + JWT + SSE. LLM = **Gemini**(`gemini-2.5-flash`).

- **레이어 경계**: API → Service → **`NavigatorAgent` 파사드(`base.py`)** → agents 내부. **service는 파사드만 호출**(graph·ideal·sub_agent 직접 import 금지).
- **폴더** `agents/navigator/`: `constants`·`schemas`·`state/`·`ideal.py`(extract/clamp/propose/compare)·`behavior_map.py`(13→8 파생)·`gemini.py`·`streaming.py`·`prompts/`·`nodes/`(interpret→respond 챗 그래프)·`graph.py`·`base.py`(파사드)·`sub_agent/`(guide ✅ / youtube ⬜)·`tools/`(LLM function-calling 예약).
- **레이어 파일**: `repositories/navigator_repository.py`·`services/navigator/service.py`·`schemas/navigator.py`·`api/v1/navigator.py`.

## 3. 핵심 설계 결정

| 항목 | 결정 |
|---|---|
| 이상향 본질 | **13축 설계(가치관10+기질3) → 8축 파생**(`behavior_map.derive_8_from_13`). LLM은 `IdealValuesDesign`(13축) 출력, 8축은 규칙 파생 |
| 8축 정의 | `exploration, analytical, creativity, execution, achievement_drive, autonomy, sociality, sensitivity` (0~100) |
| 21축 역할 | 분석 입력(근거). 13축은 "어떤 방향 이상향이 의미 있나" 근거, 8축은 현재 행동 |
| 프로파일러 분리 | 네비게이터가 **자체 13축 스키마 + derive 함수** 보유(profiler import 안 함). 순수 상수(축 라벨 `SCORE_LABELS_KO`)만 공유 |
| 근거 추적 | `user_ideal_persona.source_profile_history_id`(FK→`user_profile_history.id`) — 어느 스냅샷에서 나왔는지 고정(재현·버전고정) |
| 영속 | `user_ideal_persona`: 8축 + `values_temperament`(13축 JSONB) + `persona_label` + `description`(=type+reasoning). **유저당 여러 이상향 보관, 1개만 `is_active`** |
| 제안 캐시 | `navigator_proposal_cache`(user_id, source_profile_history_id) UNIQUE — 같은 스냅샷=같은 3안. `?refresh=true`로 재생성 |
| 가이드 그라운딩 | `sub_agent/guide/` 자율 루프(retrieve→generate→evaluate). 약한 축 top3 → `user_watch_catalog` embedding cosine RAG → 실시청 근거 가이드. 근거 없으면 폴백 |
| 챗 그래프 | 2노드 선형(interpret→respond), evaluator 없음. `event: ideal`로 갱신 8축+13축 JSON 스트리밍(레이더·바 실시간) |
| 마이그레이션 | **통합 스키마 `001_initial_schema`가 현재 head**(007~013 통합됨). 새 컬럼은 `down_revision="001_initial_schema"` |

## 4. API (모두 `Depends(get_current_user_dep)`)

| Method | Path | 설명 |
|---|---|---|
| GET | `/navigator/proposals?refresh=` | 21축 → 반대·강점심화·균형 3종(캐시) |
| POST | `/navigator/chat/stream` | 대화형 이상향 설계 (SSE: status/token/ideal) |
| POST | `/navigator/ideal` | 이상향 확정 저장 |
| GET | `/navigator/ideals` | 이상향 목록 |
| GET | `/navigator/ideal/{id}` | 이상향 단건 |
| POST | `/navigator/ideal/{id}/apply` | 적용(1개만 active) |
| GET | `/navigator/ideal/{id}/comparison` | 현재 vs 이상향 gap(8축+13축) |
| GET | `/navigator/ideal/{id}/guide?refresh=` | 행동 가이드(시청 RAG 그라운딩, 캐시) |

## 5. 구현 현황

| 영역 | 상태 |
|---|---|
| 백엔드(8 엔드포인트 + 3계층 + 파사드) | ✅ 완료 |
| 21축화(13축 설계→8축 파생, `behavior_map`) | ✅ 완료 |
| 제안 3안 캐싱(`navigator_proposal_cache`) | ✅ 완료 |
| 가이드 RAG 서브에이전트(`sub_agent/guide/`) | ✅ 완료 |
| 다개 이상향 + 적용(1개) | ✅ 완료 |
| 정적검증(ruff·compile·import·라우트) | ✅ 통과 |
| 에이전트 스모크(실 Gemini) | ✅ 통과 (`scripts/navigator_smoke.py`) |
| HTTP 전체 E2E(DB·인증·영속) | ✅ 통과 |
| 프론트 ideals 실 API 연결(JWT) | ✅ 완료 (tsc 통과) |
| **가이드 RAG 그라운딩 실검증** | ✅ 통과 (2026-06-24, `scripts/navigator_guide_rag_verify.py` — 실 pgvector + grounded 가이드가 실시청 채널 인용) |
| 옛 navigator 프론트 스택 제거 | ✅ 완료 (NavigatorPage·`lib/navigator/*`·`components/navigator/*` 삭제, ideals 단일화) |

### 프론트 구조 (현재)
- 실 연동: `lib/ideals/api.ts`(apiFetchAuth, 8 엔드포인트 + `streamChat` SSE), `components/ideals/{CompareBars,RadarCompareChart}`, `IdealSetupPage`/`IdealManagementPage`/`IdealDetailPage`.
- 옛 `lib/navigator`·`components/navigator`·`pages/agents/NavigatorPage`는 **제거됨**(목 기반·삭제된 옛 백엔드 호출). `/agents/navigator`는 제네릭 `AgentDetailPage`로 fallback.

## 6. 남은 작업

- [ ] **① YouTube 재생목록 자동생성** → [PLAN_youtube_playlist.md](./PLAN_youtube_playlist.md)
  - Gemini Google 검색 그라운딩으로 이상향 맞춤 채널 발굴 → `forHandle`/URL 파싱 → RSS → 자기교정 sub-agent. Phase A(추천 목록, OAuth 무변경) / Phase B(실제 저장, `youtube` 쓰기 스코프).
- [ ] **② 익스텐션 YouTube DOM 자동화 시청**(알고리즘 형성) — 익스텐션 기반 별개 작업. `tools/` LLM 도구 검토.
- [ ] (선택) `ideal.compare`/`clamp` 단위 테스트.

## 7. 알려진 제약 / 메모

- `python` 직접 호출 깨짐(스토어 스텁) → **모든 명령은 `uv run`**.
- 한글 JSON 본문은 Windows .exe 인자로 깨짐 → 파일(`--data-binary @file`)로 전송.
- dev 컨테이너는 `./backend/app`만 마운트(alembic `versions/` 미마운트) → 마이그레이션은 `docker cp` 후 컨테이너 내 `alembic upgrade head`(또는 호스트에서 localhost DB 대상 `uv run alembic upgrade head`).
- 네비게이터 챗 로그 = `ai_chat_logs`(agent_type=`NAVIGATOR`), RAG 미사용이라 `content_embedding`=NULL.
- LLM = Gemini. `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` 필요. 가이드 RAG·임베딩은 `OPENAI_API_KEY`(text-embedding-3-small).
