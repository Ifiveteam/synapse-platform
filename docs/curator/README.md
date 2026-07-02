# Curator 에이전트

유저의 YouTube 시청 데이터(Takeout 기반)를 분석해 답변하고, 재생목록 생성·스크랩 저장 등을 실제로 수행하는 LangGraph 에이전트. 웹 프론트 홈 화면 채팅으로 연동된다.

> 2026-07-02 기준 최신 상태. 이 문서는 `engine.py`/`tools.py`가 바뀌면 같이 업데이트해야 한다.

## API (`/api/v1/curator`)

인증: Bearer JWT (`get_current_user_dep`) 필수.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/stream` | SSE 스트리밍 (`CuratorChatRequest` — message, session_id, image_base64/mime_type) |
| `GET` | `/sessions` | 본인 큐레이터 세션 목록 |
| `DELETE` | `/sessions/{session_id}` | 세션 삭제 |
| `GET` | `/sessions/{session_id}/messages` | 세션 대화 타임라인 |

SSE 이벤트 타입: `status`(진행 상태 문구), `token`(답변 스트리밍 조각), `chart`(레이더/영상목록 등 시각화 데이터, JSON 문자열).

## 아키텍처 — 단일 agent 오케스트레이터

과거(~2026-07-01)엔 `agent`(툴 선택) → `respond`(별도 최종 답변 생성) 두 단계였지만, 2026-07-02에 `respond` 노드를 완전히 제거했다. 지금은 `agent_node` 하나가 툴 선택 + 최종 답변 생성(스트리밍)을 모두 담당하는 **LLM 오케스트레이터** 구조다.

```
START
  ↓
[agent] ── 시스템 프롬프트(툴 규칙 + 답변 규칙 + 오늘 날짜 + <최근_대화> + <유저_데이터>)
  │         + 이번 턴 메시지만 넣고 llm_with_tools.astream() 호출
  │         (툴콜 없으면 여기서 이미 답변 텍스트가 스트리밍되어 유저에게 감)
  │
  ├─ tool_calls 있음? ──────────────────────────────┐
  │                                                  ↓
  │                                              [tools] (ToolNode 실행)
  │                                                  │
  │                              action 툴인가? (create_playlist/save_scrap)
  │                                    ├─ YES → [relay] → 툴 결과 그대로 스트리밍 → END
  │                                    └─ NO  → 다시 [agent]로 (툴 결과 보고 재판단)
  │
  └─ tool_calls 없음 → END (이미 스트리밍된 답변이 최종 답)
```

**왜 respond를 없앴는가:** `agent`가 툴 없이 답할 때도 자기 답변을 만들어놓고 버린 뒤, `respond`가 컨텍스트를 수동으로 재구성해 또 한 번 생성하는 이중 구조였다. 이 수동 재구성 과정에서 에코(관련 없는 이전 답변 재활용)·날짜 환각·무관정보 재활용 버그가 반복돼서, 이중 생성 자체를 없애고 단일 경로로 통합했다.

**에코 방지 설계:** 실제 Gemini 대화 turn(`contents`)에는 **이번 턴 메시지만** 넣는다(`_build_turn_messages` — 마지막 `HumanMessage`부터). 과거 완료된 턴은 절대 `role: model` turn으로 섞지 않고, `_build_recent_context`로 요약해 시스템 프롬프트 안 `<최근_대화>` 참고 블록에만 넣는다 — 지시어("그거", "그 중에") 해석용이며, 주제가 바뀌면 절대 재사용하지 말라는 반례가 프롬프트에 명시돼 있다.

## 시스템 프롬프트 구조 (`engine.py::_SYSTEM_PROMPT_BASE`)

하나의 텍스트 블록으로 구성되며 크게 두 섹션:

- **툴 호출 규칙**: 어떤 말이 나오면 어떤 툴을 부를지 매핑(재생목록→create_playlist, URL저장→save_scrap, 유저 데이터 질문→query_db 등). 액션 툴(재생목록/스크랩) 두 개만 `_ACTION_TOOL_TRIGGERS` 키워드 매칭으로 코드에서 `tool_choice`를 강제 지정해 LLM 판단을 오버라이드한다 — 나머지는 전부 LLM 자율 판단(오케스트레이터 패턴).
- **답변 원칙**: 마지막 메시지에만 답하기, `<최근_대화>` 오남용 금지, 자기소개 금지, 마크다운 활용, 데이터 없으면 지어내지 않기 등.

매 `agent_node` 호출마다 `_build_system_prompt()`가 아래를 동적으로 조립한다:
- `[오늘 날짜]` — KST 기준 실제 날짜 (`_current_date_kst()`). 없으면 Gemini가 날짜를 지어낸다.
- `<최근_대화>` — 과거 턴 요약 (에코 방지용, 위 참고)
- `<유저_데이터>` — 이번 턴에 실행된 `ToolMessage` 결과 전부

## 툴 6개 (`tools.py::build_tools`)

| 툴 | 종류 | 설명 |
|---|---|---|
| `query_db` | 조회 | **NL2SQL** — LLM이 `DB_SCHEMA`를 보고 SELECT문을 직접 생성, 실행 전 안전장치(테이블명 검증+자동교정, user_id 강제 삽입, 위험 키워드 차단)를 거쳐 실행 |
| `search_videos` | 조회 | 벡터 검색으로 특정 주제 시청 영상 검색 |
| `search_analysis` | 조회 | 벡터 검색으로 영상 분석 내용 검색 |
| `get_persona_radar` | 조회 | 성향 vs 이상향 레이더 차트 |
| `create_playlist` | 액션 | `navigator` 에이전트(`NavigatorService.create_playlist`) 재사용 — 재생목록 생성 로직은 curator에 따로 없음 |
| `save_scrap` | 액션 | `archiver` 에이전트(`classify_scrap_content`) + 공통 `ScrapRepository` 재사용 |

**NL2SQL을 쓰는 이유:** "어떤 질문이든 답해야 한다"는 요건 때문에, 조회 종류별로 툴을 하나씩 만드는 방식(과거 15개)은 확장성 한계가 있어 스키마 기반 SQL 직접 생성으로 전환했다. 대신 LLM이 SQL을 잘못 쓰는 리스크(테이블명/컬럼명 오타, 문법 오류)가 있어 `query_db` 내부에 여러 안전장치가 들어 있다.

### `query_db` 안전장치 (2026-07-02 추가/보강)

| 문제 | 안전장치 |
|---|---|
| 존재하지 않는 테이블명(`user_subscriptions` 등 단복수 혼동) | 실행 전 `_KNOWN_TABLES`로 검증, 단복수 오타는 자동 교정 후 실행 |
| `user_id` 조건 누락 | 강제 삽입하되, `GROUP BY`/`ORDER BY`/`LIMIT`/`HAVING`보다 **앞에** 삽입 (끝에 붙이면 집계 쿼리에서 SQL 문법 오류가 남) |
| 컬럼명 오타(`channel_name`, `play_time` 등 실존하지 않는 컬럼) | 실행 실패 시 `DB_SCHEMA` 전문을 에러 메시지에 다시 포함해 재시도 유도 (스키마를 말로만 참고하라고 하는 것보다 효과적) |
| DB 에러 발생 시 세션 트랜잭션 오염 | 예외 발생 시 `await db.rollback()` 필수 — 안 하면 같은 요청의 재시도는 물론 대화 기록 저장(INSERT)까지 전부 실패한다 |
| raw DB 에러 텍스트 유출 | 모든 예외를 사용자 안전 문구로 치환, 원본은 `logger.warning`으로만 남김 |

## 소스 위치

| 경로 | 역할 |
|---|---|
| `backend/app/agents/curator/engine.py` | LangGraph 정의 — `agent_node`(툴선택+답변생성), `tools`, `relay_node`, 시스템 프롬프트 조립 |
| `backend/app/agents/curator/tools.py` | 6개 툴 + `DB_SCHEMA` + `query_db` NL2SQL 안전장치 |
| `backend/app/agents/curator/constants.py` | 모델명, 히스토리 윈도우 등 런타임 상수 |
| `backend/app/agents/curator/streaming.py` | SSE 직렬화 (Archiver와 동일 포맷) |
| `backend/app/agents/curator/types.py` | `CuratorState`, `CuratorStreamEvent` |
| `backend/app/services/curator_service.py` | 세션/히스토리 로드(최근 10개, `HumanMessage`/`AIMessage`만 — `ToolMessage`는 DB에 영속화 안 됨), SSE 저장, 세션 제목 생성 |
| `backend/app/api/v1/curator.py` | HTTP 라우터 |
| `backend/app/schemas/curator.py` | Pydantic 요청/응답 스키마 |
| `frontend/src/components/home/` | 채팅 UI (`chat-messages.tsx`, `curator-input.tsx`, `chart-block.tsx`) + 채팅 테마 커스터마이징 |
| `frontend/src/stores/chat.ts`, `chat-theme.ts` | 대화 상태, 테마 프리셋(Zustand persist) |

과거에 있던 `backend/app/agents/curator/steps/`(`respond.py` 포함)는 2026-07-02에 삭제됐다 — 더 이상 존재하지 않는다.

## 알려진 제약 / 데이터 한계

- **구독 채널 정보는 Takeout 전체 ZIP 업로드에서만 채워진다** (`app/agents/indexer/nodes/preprocess.py`). 시청 기록(watch-history) JSON/HTML만 업로드한 유저는 `user_subscription` 테이블이 항상 비어 있는 게 정상이며, 버그가 아니다. `query_db`가 이 경우 원인을 설명하는 안내 메시지를 반환한다.
- **`user_watch_catalog`에는 시청 시간(duration/play_time) 컬럼이 없다** — "얼마나 오래 봤어?" 류 질문은 스키마상 답할 수 없는 질문이다.

## 남은 이슈 (2026-07-02 기준 미해결)

- [ ] 컬럼명 환각이 완전히 해결됐는지 라이브 재확인 필요 (에러 시 스키마 재제공 방식은 오프라인 검증만 끝남)
- [ ] 자기소개 반복 금지 규칙이 실제로 잘 지켜지는지
- [ ] 세션 제목 생성 품질
- [ ] "그 중에 야구만" 같은 지시어 후속 질문의 툴 파라미터 정확도
- [ ] `bind_tools()` + `astream()` 스트리밍 조합이 액션 툴(재생목록 등) 경로에서도 안정적인지 추가 테스트

## 디버깅 팁

큐레이터에서 이상 동작이 보이면 스크린샷만으로 추측하지 말고 **백엔드 컨테이너 로그부터 확인**한다:

```
docker logs synapse-backend-dev --tail 200
```

2026-07-02에 발견된 실제 원인들(Gemini API 크레딧 소진 429, 컬럼명 환각으로 인한 `UndefinedColumnError`, 트랜잭션 poisoning으로 인한 대화 기록 저장 실패, hot-reload 재시작으로 인한 스트림 끊김)은 전부 이 로그에서 몇 초 만에 확인됐다.
