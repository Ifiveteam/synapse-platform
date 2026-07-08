# Navigator

프로파일러 분석을 근거로 **이상향(이상 자아)을 제안·대화 설계·보관·적용**하고, 이상향+시청기록 기반 **행동 가이드**와 **YouTube 재생목록**을 만드는 에이전트.

> 이 문서 하나로 전체 설계·그래프·API·재생목록을 다룬다(과거 `PLAN.md`·`PLAN_youtube_playlist.md` 통합). ERD: [../erd.md](../erd.md).

## 1. 제품 플로우
1. 프로파일러 산출물을 입력으로 — **주 신호 = `portrait`(성향 6축 + 관심 도메인 9축)**, 21축(가치10+기질3+행동8)은 보조 근거.
2. **반대 / 강점심화 / 균형** 이상향 3안 자동 제안 (스냅샷별 캐시, 비동기 생성).
3. **챗봇 대화(SSE)** 로 이상향을 설계·조율 → 목표 성향·관심 도메인·관심 키워드 확정.
4. **현재 vs 이상향** 비교(gap).
5. 이상향 기반 **행동 가이드** 생성 (시청기록 RAG 그라운딩).
6. 이상향 기반 **YouTube 재생목록** 생성 → 편집 → **실제 YouTube 저장**(Phase B) → **자동 갱신**(주기 스케줄러).

## 2. 아키텍처

**Archiver 패턴 미러링** — stateless LangGraph + service(영속) + repository(asyncpg) + JWT + SSE. LLM = **Gemini**. 임베딩·가이드 RAG = OpenAI `text-embedding-3-small`.

- **레이어 경계**: API → Service → **`NavigatorAgent` 파사드(`facade.py`)** → agents 내부. service는 파사드만 호출.
- **폴더** `agents/navigator/`: `constants`·`schemas`·`state/`·`ideal.py`(`propose_ideals`)·`axes.py`(extract/clamp/compare·`disposition_from_portrait`·`interest_from_portrait`·`coerce_interest_targets`)·`behavior_map.py`(13→8 파생)·`llm.py`·`streaming.py`·`prompts/`·`nodes/`·`graph.py`·`facade.py`·`sub_agent/`(guide ✅ / youtube ✅).
- **레이어 파일**: `repositories/navigator_repository.py`·`services/navigator/service.py`·`services/playlist_refresh_scheduler.py`·`schemas/navigator.py`·`api/v1/navigator.py`.

## 3. 챗 그래프 (이상향 설계)

**파일:** `graph.py::build_navigator_graph`. 노드는 3개이며 파일명↔노드명이 다르다(`nodes/__init__.py` alias): `assess`=`interpret.py`, `ask`=`respond.py`, `finalize`=`finalize.py`.

```text
일반 턴 : START → [assess ∥ ask] → END        (병렬 — respond가 assess 갱신을 기다리지 않고 스트리밍)
확정 턴 : START → assess → finalize → END
```
라우팅: `route_start` / `route_after_assess`.

- **`assess`**: 매 턴 목표 성향·관심 도메인·관심 키워드를 갱신하고 `interest_keywords`를 `working_keywords`로 누적. `event: ideal` payload = `{disposition, interest, behavior, values_temperament, keywords}`(5필드) 스트리밍(레이더·바 실시간).
- **`ask`**: 사용자에게 되묻는 대화 응답을 `token`으로 병렬 스트리밍.
- **`finalize`**: 확정 시 `complete` 이벤트로 `{disposition, interest, behavior, values_temperament, persona_label, reasoning, keywords, ideal_type=CUSTOM}` 방출.
- facade 허용 이벤트: `{status, token, ideal, complete}`.

## 4. 핵심 설계 결정

| 항목 | 결정 |
|---|---|
| 이상향 주 신호 | **portrait(성향 6축 + 관심 도메인 9축)**. LLM이 `target_disposition`·`target_interest`를 직접 설계. 13축은 보조 + 8축 파생용(`behavior_map.derive_8_from_13`) |
| 8축 정의 | `exploration, analytical, creativity, execution, achievement_drive, autonomy, sociality, sensitivity` (0~100) |
| 관심 키워드 | 대화에서 뽑은 구체 키워드를 `taste_keywords`(JSONB)에 저장 — 재생목록 검색 **최우선 씨앗** |
| 근거 추적 | `user_ideal_persona.source_profile_history_id`(FK→`user_profile_history.id`) — 유발 스냅샷 고정 |
| 영속 | `user_ideal_persona`: 8축 + `values_temperament`(13축) + `target_disposition`·`target_interest`·`taste_keywords` + `persona_label` + `description`. **유저당 여러 이상향, 1개만 `is_active`** |
| 제안 캐시 | `navigator_proposal_cache`(user_id, source_profile_history_id) UNIQUE. `status`(pending/ready/failed) + `dismissed`/`consumed` 상태. **비동기 생성**(백그라운드 예약 후 프론트 폴링), stale-pending 자가치유(180초), failed 자동 재생성. `?refresh=true`로 새로 생성 |
| 가이드 그라운딩 | `sub_agent/guide/` 자율 루프(retrieve→generate→evaluate). 약한 축 top3 → `user_watch_catalog` embedding cosine RAG → 실시청 근거 가이드. 근거 없으면 폴백 |
| 마이그레이션 | head = **`019_playlist_last_refreshed_at`**. navigator 관련: 013(targets)·014(playlist status)·015(save_status)·016(proposal status)·017(taste_keywords)·018(refresh_period)·019(last_refreshed_at). 새 마이그레이션은 `down_revision`을 직전 head로. 표는 [../erd.md](../erd.md) |

## 5. API (모두 `Depends(get_current_user_dep)`, `api/v1/navigator.py`)

### 이상향 설계·보관·적용
| Method | Path | 설명 |
|---|---|---|
| GET | `/navigator/proposals?source_profile_history_id=&refresh=` | 3안 조회/생성 (**비동기** — 없음/refresh/stale면 status=pending 반환, 폴링) |
| GET | `/navigator/proposals/active` | 진행 중(추천 생성 중) 여부 — 관리 화면 배너 |
| DELETE | `/navigator/proposals/active` | 배너 닫기(최신 추천 dismissed) |
| POST | `/navigator/chat/stream` | 대화형 설계 SSE (status/token/ideal/complete) |
| GET | `/navigator/chat/history?session_id=` | 설계 대화 이력(이어서 설계) |
| POST | `/navigator/ideal` | 이상향 확정 저장 |
| GET | `/navigator/ideals` · `/navigator/ideal/{id}` | 목록 / 단건 |
| POST | `/navigator/ideal/{id}/apply` | 적용(1개만 active) |
| DELETE | `/navigator/ideal/{id}` | 삭제(연관 재생목록 CASCADE) |
| GET | `/navigator/ideal/{id}/comparison` | 현재 vs 이상향 gap(성향·도메인·8축) |
| GET | `/navigator/ideal/{id}/guide?refresh=` | 행동 가이드(시청 RAG, 캐시) |

### 재생목록 (이상향 1 : N)
| Method | Path | 설명 |
|---|---|---|
| POST | `/navigator/ideal/{id}/playlists` | 새 재생목록 생성 (`{refresh_period}` optional, **비동기** pending→폴링) |
| GET | `/navigator/ideal/{id}/playlists` | 목록 |
| GET/PATCH/DELETE | `/navigator/playlists/{id}` | 단건 / 제목 수정 / 삭제 |
| PATCH | `/navigator/playlists/{id}/period` | 자동 갱신 주기 변경(none/weekly/monthly) |
| POST | `/navigator/playlists/{id}/item/refresh` | 영상 1개 교체(저수지→채널 re-RSS) |
| POST | `/navigator/playlists/{id}/regenerate` | 전체 재생성(같은 행 pending 갱신) |
| POST | `/navigator/playlists/{id}/save` | 실제 YouTube 저장 시작(**비동기**, `needs_reconsent`면 재동의) |
| POST | `/navigator/playlists/{id}/chat` (SSE) | 채팅 부분수정(status + 최종 playlist) |

## 6. YouTube 재생목록

적용/선택한 **이상향** + **시청 기록**을 근거로 영상 **10개**를 추천하고, 사용자가 영상별 새로고침/채팅으로 다듬은 뒤 본인 YouTube 계정에 실제 재생목록으로 저장한다. 진입 UX: 이상향 상세에서 [재생목록 추천] → 그 이상향의 재생목록 뷰.

### 데이터 모델 — `navigator_playlist`
| 컬럼 | 설명 |
|---|---|
| `id`·`user_id`·`ideal_id`(FK CASCADE) | 이상향당 N개 |
| `title` | 자동 `{persona_label} #N`, 사용자 수정 가능 |
| `summary` | 총평(LLM 큐레이션) |
| `items_json` | 영상 10개 |
| `channels_json` | 발굴·선택 채널 `{channel_id, title}` — re-RSS 무쿼터 보충 |
| `reservoir_json` | 여분 영상(즉시 교체용) |
| `status` | 생성 상태 pending/ready/failed (014) |
| `save_status` | YouTube 저장 상태 none/saving/saved/failed (015) |
| `refresh_period` | 자동 갱신 주기 none/weekly/monthly (018) |
| `last_refreshed_at` | 마지막 (재)생성 시각, 주기 도래 판정용 (019) |
| `youtube_playlist_id` | 실제 저장 후 채워짐 |

인덱스 `ix_np_user_ideal (user_id, ideal_id)`. 근거(카테고리·채널·시청영상)는 `user_watch_catalog`에서 읽기만.

### 서브에이전트 — `sub_agent/youtube/`
```text
[생성]  discover(검색어→search?type=channel) → pick(채널선택) → collect(RSS) → evaluate(자기교정) → curate(10개+이유)
[편집]  interpret(요청해석) → (필요시 discover) → curate(부분수정)   ← human-in-the-loop 재진입
```
- **검색 근거 우선순위**: `taste_keywords`(대화 키워드) > 9개 관심 도메인. `_raise_domains`가 `target − current > 0` 도메인 top-K를 "넓힐 목표"로 주입해 다양성 강제(`prompts.py::build_query_prompt`, `graph.py::_raise_domains`).
- **채널 발굴**: `search?type=channel`(1콜=실재 채널 25개, 100유닛)로 channelId 보증(환각 0) → RSS(무료) → 안 본 새 영상. LLM은 검색어·선택·이유만, id는 search/RSS 소유.
- **필터**: 쇼츠 제외(`filter_out_shorts`+`fetch_video_durations`), 오래된 영상 제외(`is_too_old`, `MAX_VIDEO_AGE_DAYS`).
- **보충 우선순위**: ① `reservoir`(즉시) → ② `channels_json` re-RSS(무료) → ③ 검색(새 주제만). 자기교정/편집 루프는 `MAX_ATTEMPTS` 가드.

### 생성·저장·갱신 흐름
- **생성/재생성은 비동기**: `create_playlist`가 빈 `pending` 행을 즉시 만들고 `_spawn_bg(_generate_playlist_bg)` → 프론트 폴링. `regenerate_playlist`도 같은 행 pending 갱신.
- **저장(Phase B, 구현 완료)**: `save_playlist_to_youtube` → 토큰 없으면 `SaveStartResponse(needs_reconsent=True)`(재동의 유도), 있으면 `_save_playlist_bg`가 save_status=saving→`create_youtube_playlist`→영상 순차 `add_playlist_item`→`youtube_playlist_id` 채우고 saved. `YOUTUBE_SCOPE`/`get_youtube_access_token`(`services/google_oauth.py`). 쓰기 스코프는 기본 `SCOPES` 밖이라 needs_reconsent 흐름 존재.
- **자동 갱신**: `services/playlist_refresh_scheduler.py::scheduler_loop`(TICK 기본 3600s, `MAX_PER_TICK=5`, `_PERIOD_DAYS={weekly:7, monthly:30}`)가 `main.py` lifespan에서 백그라운드 기동. 주기 도래(`_is_due`) 재생성.

## 7. 알려진 제약 / 메모
- LLM = Gemini(`GOOGLE_API_KEY` 또는 `GEMINI_API_KEY`). 가이드 RAG·임베딩 = `OPENAI_API_KEY`. 재생목록 = `YOUTUBE_API_KEY`(client.py). 스케줄러 주기 = `PLAYLIST_REFRESH_TICK_SECONDS`.
- 쓰기 쿼터: 10개 저장 ≈ 550유닛(50 + 50×10). 사용자 트리거 1회.
- 네비게이터 챗 로그 = `ai_chat_logs`(agent_type=`NAVIGATOR`), RAG 미사용이라 `content_embedding`=NULL.
- **코드 정합 메모**: `set_playlist_period` docstring 2곳(`service.py`·`api/v1/navigator.py`)에 실제 미지원 값 `daily`가 오기돼 있음(스키마 `PlaylistPeriod`·스케줄러는 none/weekly/monthly만). 미사용 스키마 `SavePlaylistResponse` 정리 검토.
- dev 컨테이너는 `./backend/app`만 마운트(alembic `versions/` 미마운트) → 마이그레이션은 `docker cp` 후 컨테이너 내 `alembic upgrade head`.
