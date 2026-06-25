# Navigator 구현 계획

> 상태: 백엔드 1차 구현 완료 (lint·graph·app import 통과). 진행 현황은 [PROGRESS.md](./PROGRESS.md).
> 범위: **백엔드만**. 익스텐션 YouTube 조작·재생목록은 다음 단계.
> 폴더 컨벤션: 파이프라인 스타일(`graph.py`+`state/`+`nodes/`+`sub_agent/`) + 기능 분리(`ideal.py`·`guide.py`) + 파사드(`base.py`). 챗(SSE)에 archiver 부품(`gemini.py`·`streaming.py`·`constants.py`) 차용. **`tools/`는 LLM function-calling 도구 전용**(코드가 부르는 기능과 구분).

## 1. 배경 (Context)

기존 navigator 백엔드(`agents/navigator/`, `api/v1/navigator.py`)는 옛 8축
(`intellectual_curiosity` 등)에 묶여 있고 DB·인증·스키마 레이어가 없어 **전부 삭제**했다
(앱 정상 기동 확인). 이제 새 축 체계로 재구현한다.

**제품 플로우**
1. 프로파일러가 산출한 **21축 프로필**을 입력으로
2. **반대 / 강점심화 / 균형(약점보완) 이상향 3종**을 자동 제안
3. **챗봇 대화(SSE)** 로 이상향을 설계·조율
4. **현재 분석 vs 이상향**을 비교(gap)
5. 이상향 기반 **행동 가이드** 생성
6. (다음 단계) 익스텐션으로 **YouTube 직접 조작(알고리즘 형성) + 재생목록 추천**

## 2. 확정 설계 결정

| 항목 | 결정 |
|------|------|
| 이상향 축 | **Synapse 행동 8축** (`exploration, analytical, creativity, execution, achievement_drive, autonomy, sociality, sensitivity`), 0~100 스케일 |
| 21축 역할 | **분석 입력(근거)** 으로만 사용. 13축(가치관10+기질3)은 "어떤 방향 이상향이 의미 있나" 판단 근거, 8축은 현재 행동 |
| 13축 저장 | **숫자 미저장** (이미 `user_profile_history`에 존재) |
| 근거 추적 | 13축 복제 대신 **`source_profile_history_id`(UUID FK→`user_profile_history.id`) 1컬럼 추가**. 이상향이 어느 21축 스냅샷에서 나왔는지 고정 → 재현·감사. **가벼운 alembic 마이그레이션 1회 필요** |
| 영속화 | `user_ideal_persona`(8축 + `description` + `source_profile_history_id`). `description`에 `ideal_type` + 근거(reasoning) 기록. **유저당 1행 upsert** (UK 없음 → select 후 update/insert) |
| 아키텍처 | **Archiver 패턴 미러링** — stateless LangGraph + service(영속화) + repository(AsyncSession) + JWT + SSE |
| LLM | **Gemini** (`gemini-2.5-flash`, archiver/profiler와 동일) |
| 챗 그래프 | **2노드 선형** (`interpret`→`respond`), evaluator 루프 없음 |
| 레이더 동기화 | 챗 중 토큰 외에 갱신된 8축 JSON을 별도 `event: ideal` 1회 전송 |

## 3. 재사용 자산 (신규 작성 최소화)

| 용도 | 재사용 대상 |
|------|-------------|
| 최신 프로필 | `repositories/profiler_repository.py::fetch_latest_profile(session, user_id)` |
| 21축 dict | `services/profiler/scores.py::history_scores_dict(row)`, `SCORE_FIELDS` |
| 축 한글 라벨 | `agents/profiler/axis_labels.py::SCORE_LABELS_KO` |
| top 관심사 | `repositories/indexer_repository.py::fetch_top_categories / fetch_top_channels(limit=5)` |
| JWT / 세션 | `api/v1/auth.py::get_current_user_dep`, `core/database/session.py::get_db` |
| 채팅 로그 | `models/chat.py::AIChatLog` (agent_type=`NAVIGATOR`, `content_embedding=None`) |
| 히스토리→messages | `agents/archiver/history.py` (agent 무관, 재사용) |
| SSE·엔진·스텝 패턴 | `agents/archiver/{engine,streaming,gemini,constants}.py`, `steps/respond.py` |
| persist 정책 | `services/archiver_service.py::should_persist_assistant_log` |
| 이상향 모델 | `models/user_ideal_persona.py::UserIdealPersona` |

## 4. 폴더 구조 (신규)

```
backend/app/agents/navigator/
├── __init__.py
├── constants.py     # BEHAVIOR_AXES(8) SSOT, GEMINI_MODEL, NAVIGATOR_AGENT_TYPE, temps, MAX_HISTORY_MESSAGES, STREAM_ERROR_*
├── schemas.py       # 내부 도메인 Pydantic — IdealType, IdealRadar/IdealAdjustment/AxisGap/RadarComparison/Guide, NavigatorStreamEvent
├── state/
│   ├── __init__.py
│   └── navigator.py # NavigatorState(TypedDict, messages=add_messages)
├── ideal.py         # 기능: extract_8axis, clamp, propose_ideals()->3종[Gemini], compare()[순수]
├── guide.py         # 기능: generate_guide()[Gemini]
├── tools/           # (예약) LLM function-calling 도구 모음 — YouTube 등 (코드 기능과 구분)
│   └── __init__.py
├── gemini.py        # Gemini client (invoke_structured/_safe, get_client)
├── streaming.py     # SSE envelope (event:/data:{"content"})
├── base.py          # NavigatorAgent 파사드 — tool·graph 조율 소유 (propose/compare/generate_guide/normalize_ideal/current_axes/chat_stream), get_navigator_agent() 싱글톤
├── graph.py         # build_navigator_graph()만 (StateGraph 빌드·컴파일)
├── nodes/
│   ├── __init__.py
│   ├── _common.py   # latest_user_message, to_gemini_contents
│   ├── interpret.py # 유저 메시지 → working_ideal 조정(structured) + status·ideal 이벤트
│   └── respond.py   # 설명 토큰 스트리밍 (get_stream_writer)
├── prompts/
│   ├── __init__.py  # render 헬퍼 (21축/8축/관심사)
│   ├── propose.py
│   ├── chat.py
│   └── guide.py
└── sub_agent/
    └── __init__.py  # (다음 단계) YouTube 조작·재생목록 자리

backend/app/services/navigator/                  # 서비스 패키지 (다음 단계 youtube·playlist 자리)
├── __init__.py                                  #   NavigatorService 재노출
└── service.py                                   #   오케스트레이션·영속화·SSE 직렬화
backend/app/repositories/navigator_repository.py # user_ideal_persona upsert/get + AIChatLog(NAVIGATOR) CRUD
backend/app/schemas/navigator.py                 # HTTP DTO 분리
backend/app/api/v1/navigator.py                  # 라우터(인증 필수)
```
- `api/v1/__init__.py`에 `navigator_router` 재등록 (import + `include_router`).
- `models/user_ideal_persona.py`: `source_profile_history_id`(UUID, FK→`user_profile_history.id`, `ondelete="SET NULL"`, nullable) 컬럼 추가.
- `alembic/versions/XXX_add_source_profile_to_ideal_persona.py`: 위 컬럼 추가 마이그레이션.

## 5. 핵심 시그니처

**schemas.py** (내부 도메인) / **state/navigator.py** (그래프 상태)
- `IdealRadar`: 8 float(ge0 le100) + `reasoning`, `.scores()`/`from_scores()`
- `RadarComparison`: `gaps: list[AxisGap]`, `gap_by_axis: dict`, `total_gap: float`
- `Guide`: `summary`, `steps: list[GuideStep]`
- `IdealAdjustment`(챗 structured): `updated_radar`, `changed`, `note`
- `NavigatorStreamEvent`(dataclass), `StreamEventType = Literal["status","token","ideal"]`
- `NavigatorState`: `messages, user_id, session_id, profile_21, current_8axis, top_interests, working_ideal, ideal_type, ideal_reasoning, final_response, current_step, error`

**ideal.py / guide.py** (코드가 부르는 기능. `tools/`는 LLM이 부르는 도구 전용)
- `extract_8axis(profile_21)`, `clamp_value/clamp_scores`
- `async propose_ideals(profile_21, top_interests) -> list[(IdealType, IdealRadar)]` — OPPOSITE/DEEPEN/BALANCE 각 프롬프트, `asyncio.gather`(3), 출력 8축만 + clamp
- `compare(current_8, ideal_8) -> RadarComparison` — `gap = ideal - current`, 라벨 `SCORE_LABELS_KO`
- `async generate_guide(...) -> Guide` — Gemini structured

**repository** — `save_ideal(user_id, scores8, ideal_type, reasoning, source_profile_history_id)` upsert / `get_latest_ideal(user_id)` / `decode_description` / `resolve_session_id` / `get_chat_history` / `save_chat_log`(agent_type=NAVIGATOR)

**service** (글루) — `__init__(db=Depends(get_db), agent=Depends(get_navigator_agent))`; `_load_profile_or_404` → `(profile_21, current_8axis, top_interests, snapshot_id)`; 각 메서드는 `[DB 로드] → self.agent.X(...) → [DTO/SSE/저장]`. **tool·graph 직접 import 없음.**

**base (NavigatorAgent 파사드)** — `propose`, `current_axes`, `normalize_ideal`, `compare(profile_21, ideal_8)`, `generate_guide(...)`, `chat_stream(*, messages, ...) -> AsyncIterator[NavigatorStreamEvent]` (내부에서 그래프 `astream(stream_mode=["custom","values"])`)

## 6. API (모두 `Depends(get_current_user_dep)`, `user_id = user.id`)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/navigator/proposals` | 최신 21축 → 반대·강점심화·균형 이상향 3종 제안 (`proposals[]`) |
| `POST` | `/navigator/chat/stream` | 대화형 이상향 설계 (SSE) |
| `POST` | `/navigator/ideal` | 선택 이상향 확정 저장 |
| `GET` | `/navigator/ideal` | 저장된 이상향 조회 (없으면 404) |
| `GET` | `/navigator/comparison` | 현재(8축) vs 저장 이상향 gap |
| `GET` | `/navigator/guide` | 이상향 기반 행동 가이드 |

## 7. LangGraph 챗 흐름

```
START → interpret (유저 메시지 → working_ideal 조정, Gemini structured) + status 이벤트
      → respond   (조정 결과 설명 토큰 스트리밍)
      → END
multi-turn: service가 AIChatLog 히스토리를 messages로 주입 (archiver history 패턴)
```
제안(propose)·비교(compare)·가이드(guide)는 그래프 밖 일회성 호출(`ideal.py`·`guide.py`).

## 8. 구현 순서

0. **모델·마이그레이션**: `models/user_ideal_persona.py`에 `source_profile_history_id` FK 추가 + alembic 마이그레이션 → `uv run alembic upgrade head`
1. **기반(LLM 없음)**: `constants.py`, `schemas.py`, `state/navigator.py`, `schemas/navigator.py`, `ideal.py`(extract/clamp/compare), `streaming.py`
2. **영속화**: `repositories/navigator_repository.py` (save_ideal upsert[+FK], get_latest_ideal, 채팅 로그)
3. **LLM**: `gemini.py`, `prompts/*`, `tool.propose_ideals`, `tool.generate_guide`
4. **그래프·파사드**: `nodes/{_common,interpret,respond}.py`, `graph.py`(빌드), `base.py`(NavigatorAgent 파사드), `__init__.py`
5. **서비스**: `services/navigator/service.py` 6개 메서드 + `_load_profile_or_404` + SSE 누적/persist
6. **API**: `api/v1/navigator.py` + `api/v1/__init__.py` 등록

## 9. 검증 (uv 환경)

```bash
cd backend
uv run alembic upgrade head   # source_profile_history_id 컬럼 반영
uv run ruff check app/agents/navigator app/services/navigator \
  app/repositories/navigator_repository.py app/schemas/navigator.py app/api/v1/navigator.py
uv run python -c "from app.agents.navigator.graph import build_navigator_graph; build_navigator_graph(); print('graph ok')"
uv run python -c "from app.api.v1 import api_router; print([r.path for r in api_router.routes if 'navigator' in r.path])"
```
- `/docs`에서 `/navigator/*` 6개 라우트 확인
- E2E (인증 토큰 + 프로필 1건 선행): `GET /proposals` → `POST /chat/stream`(토큰 수신) → `POST /ideal` → `GET /comparison` → `GET /guide` → DB `user_ideal_persona` 1행 확인
- pytest 의존성 없음 → 검증은 lint + import + boot 중심. `ideal.compare`/`clamp` 단위테스트는 선택.

## 10. 다음 단계 (이 계획 밖)

- 익스텐션 YouTube 조작(하이브리드: 시청=DOM 자동화 / 재생목록·구독=Data API + OAuth `youtube` 스코프 추가) → `agents/navigator/sub_agent/youtube/` 서브에이전트화 검토
- 프론트 `lib/navigator`·`components/navigator`·`NavigatorPage`를 새 8축/API에 맞게 재구현
