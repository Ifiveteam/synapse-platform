# Profiler

YouTube 시청 catalog를 바탕으로 **영상 의미 분석 → 21축 성향 프로필 + portrait 초상 → 완료 이메일**까지 수행하는 에이전트.

> 이 문서 하나로 파이프라인·그래프·DB·API를 모두 다룬다. ERD: [../erd.md](../erd.md) (`video_analysis`, `user_profile_history`).

---

## 1. 트리거

| 경로 | 설명 |
|------|------|
| **인덱서 자동(배치)** | "분석 시작" 클릭 = 한 배치(`batch_id`). 업로드가 끝나면 프론트가 `POST /indexer/batch/{id}/seal`("다 보냄")을 보내고, 배치의 모든 소스 인덱싱이 끝나면 `enqueue_for_user(analysis_source_ids, batch_id)`로 **그 배치 영상만** 1회 분석 |
| **수동** | `POST /profiler/run` — `batch_id` 없음 → **통합본**(창고 전체 최근 2달) |
| **영상 분석만** | `POST /profiler/video-summary/run` (서브그래프 단독) |

> **배치 스코프**: `batch_id` 없이 온 소스(Drive 자동·구경로)는 서버가 단일 배치를 자동 생성·자동 seal한다. seal이 안 오면 `reconcile_stuck_batches`(자동-seal 안전망, WARNING 로그)가 마감한다. 트리거는 `analysis_batch.status`를 `sealed→profiling`으로 **원자 전환**한 호출만 발사(중복 방지). 킬스위치 `PROFILER_BATCH_SCOPE_ENABLED=false`면 통합본으로 산출.

---

## 2. 메인 그래프 (3노드)

**파일:** `agents/profiler/graph.py` · **상태:** `agents/profiler/state/profiler.py` (`ProfilerState`)

```text
video_summary → build_profile → notify → END
```

| 노드 | 파일 | 역할 |
|------|------|------|
| `video_summary` | `nodes/video_summary.py` | 서브그래프 `run_video_summary()` 호출 |
| `build_profile` | `nodes/build_profile.py` | 21축 점수·해석 + **portrait 초상** 산출 후 DB 스냅샷 저장 |
| `notify` | `nodes/notify.py` | portrait 기반 리치 HTML 완료 이메일 (Resend) |

---

## 3. video_summary 서브그래프 (4노드)

**파일:** `agents/profiler/sub_agent/video_summary/graph.py`

```text
select → summarize → embed → store → END
        (catalogs 비었거나 error면 select→store 로 우회, summarize error면 store 로)
```

| 노드 | 파일 | 역할 |
|------|------|------|
| `select` | `nodes/select.py` | 분석 대상 catalog 선별 (메타데이터만, 자막 미수집) |
| `summarize` | `nodes/summarize.py` | Gemini structured output — 브리프·톤·의도·가치 (동시 8건, 실패 스킵) |
| `embed` | `nodes/embed.py` | `embedding_text` → OpenAI `text-embedding-3-small` (1536) |
| `store` | `nodes/store.py` | `profiler_repository.upsert_video_analysis` (catalog 1:1, `catalog_id` UK) |

### select 분기 (3가지)

| 조건 | 동작 |
|------|------|
| `analysis_limit` 있음 (API `limit`) | 미분석 catalog N건 (`fetch_unanalyzed_catalog`) |
| `source_ids` 있음 (배치 스코프) | 배치 소속 영상 (`fetch_catalog_rows_by_sources`) → `select_analysis_sample` |
| 그 외 (통합본) | 창고 최근분 (`fetch_recent_catalog_rows`) → `select_analysis_sample` |

샘플링 규칙 (`services/profiler/sampling.py`): 롱폼/숏폼 각 상위 채널 5개당 대표 1편 + 카테고리별 상위 채널 5개당 대표 1편(중복 제거).

> 자막(`transcript`)은 youtube-transcript-api IP 차단으로 수집률 0%라 제거함(마이그레이션 008). 의미분석은 제목·설명·태그·카테고리 메타데이터만 사용.

**summarize 산출 필드** (`schemas/profiler/llm/video.py::VideoSemanticAnalysis`): `summary_kr`(브리프 3~5문장), `tones`×3, `intents`×3, `value_signals`×3.

---

## 4. build_profile — 21축 프로필

**파일:** `nodes/build_profile.py` · **프롬프트:** `agents/profiler/prompts.py` · **LLM 헬퍼:** `agents/profiler/llm.py`(`invoke_gemini_structured`) · **의미라벨 매핑:** `semantics.py`

### 입력
1. catalog → `catalog_stats`(카테고리·숏폼/롱폼 비율 등)
   - **배치 분석**: `fetch_catalog_rows_by_sources` — 배치 소스 소속 영상(조인 `analysis_source_catalog`) 합집합을 **최근 2달로 재컷**(앵커=배치 집합 내 max `watched_at`).
   - **통합본**: `fetch_recent_catalog_rows` — 창고 전체 최근 2달.
2. `video_analysis` 샘플(요약·톤·의도·가치) — 배치 분석 시 그 catalog 행들 것만.

### 점수 산출 (2단계 LLM + rule fallback)

| 단계 | 축 | 개수 |
|------|-----|------|
| 1 | Schwartz 가치관 | 10 |
| 1 | TCI 기질 | 3 |
| 2 | 행동 스파이더 | 8 |

- LLM 실패 시 단계별 rule fallback(`rule_based_values_temperament` → `rule_based_behavior_spider`) + calibration.
- 해석(`ProfileInsightOutput`): `summary_text`, `persona_label`(→ `agents/shared/persona.py::persona_from_scores`), `dominant_traits`, `behavior_reasoning`, `supporting_evidence`(내부 `insight`에 `strengths`/`weaknesses`/`content_preferences`).
- `insert_profile_snapshot(..., batch_id=, portrait=)` → `user_profile_history` (commit은 노드에서).

---

## 4b. portrait — 초상 프로필 (JSONB)

`build_profile` 노드가 21축 산출 직후 **같은 세션에서** 이어 만드는 두 번째 프로필 표현. `user_profile_history.portrait`(JSONB)에 저장(마이그레이션 011 `v2` → 012 `portrait` 개명). 산출 실패는 스냅샷을 막지 않고 스킵(로그만).

- **생성기:** `services/profiler/portrait.py::build_portrait`. 데이터 원천은 21축과 별개인 **catalog 경량 투영** `fetch_catalog_signal_rows`(카테고리·채널·태그·숏츠·재생수·길이·제목). **영상 요약(video_analysis) 미사용.**
- **LLM 호출 1회**(`_synthesize`)로 `disposition`(6축)·`keywords`·`persona_label`·`reasoning` 생성. `interest`(9도메인 레이더)·`style`(소비스타일 4지표)은 **결정적**(LLM 없음).

```jsonc
{
  "persona_label": "…",                 // LLM — 한 줄 별칭
  "keywords":      ["…"],               // LLM — 5~7개
  "interest":      [{axis, value}],     // 결정적 — 9 도메인 레이더
  "disposition":   [{axis, value}],     // LLM 6축 (몰입/탐험/팬심/트렌드민감/정보추구/감성지향)
  "style":         [{label, value}],    // 결정적 — 숏폼비율/채널집중도/관심다양성/반복시청
  "reasoning":     "…"                  // LLM — 근거 2~3문장
}
```

- **9 관심 도메인**(`_DOMAINS`): 스포츠·게임·음악·예능·인물·일상·영화·애니·뉴스시사·지식교육·라이프취미 (15개 YouTube category id → 도메인 매핑).
- **소비스타일 4지표**: 숏폼 비율, 채널 집중도, 관심 다양성(정규화 섀넌 엔트로피), 반복 시청.
- **소비처**: 완료 이메일(§5), 분석 목록 제목(`persona_label`), compare 서브에이전트, 그리고 **네비게이터가 이상향 설계의 주 신호**로 사용. → [../navigator/README.md](../navigator/README.md).

---

## 5. notify — 완료 이메일

`nodes/notify.py`가 `profile_dict_with_catalog`로 스냅샷 상세를 적재한 뒤 **portrait 중심 리치 HTML**을 만든다: 페르소나 헤더 · 키워드 해시태그 · 요약 · 강점/맹점 박스 · 관심 레이더 바차트 · 상위 3카드(상위 카테고리 / 롱폼 상위 채널 / 숏폼 상위 채널, `fetch_top_categories`/`fetch_top_channels` long·short 분리).

- 필드 우선순위 portrait-first(`_extract`): persona·summary(=`portrait.reasoning`)·keywords·interest를 portrait에서, 없으면 `profile_insight` fallback.
- 수신: `ProfilerState.notify_email`. 수동 `POST /run`·자동 `enqueue_for_user`(takeout·indexer 라우터) 모두 이메일 전달. `RESEND_API_KEY` 없으면 조용히 skip.

> 자동 트리거 태스크는 `ProfilerService._bg_tasks` 강한참조로 GC 유실 방지. 진행 상태(분류중/분석중)는 DB 기반(`user_analysis_source.status`+`stage`)이라 재시작에도 유지.

---

## 5b. compare 서브에이전트

두 `user_profile_history` 스냅샷 비교 (`sub_agent/compare/`). `GET /me/analyses/compare?from=&to=`에서 파사드 `ProfilerAgent.compare` 통해 호출.

```text
load(두 스냅샷) → diff(축별 결정적 변화) → summarize(LLM 내러티브) → END
```

`persona_label`은 각 스냅샷 portrait에서 취함. 결과 → `AnalysisCompareResponse`.

---

## 6. 비동기·Job 실행

| 구간 | 방식 |
|------|------|
| HTTP 응답 | 즉시 `202` + `job_id` |
| `POST /profiler/run` | FastAPI `BackgroundTasks` |
| 인덱서 → 프로파일러 | `enqueue_for_user`(loop.create_task, `_bg_tasks` 강한참조) |
| 그래프 | `async ainvoke` |
| **동시 실행 제한** | 전역 `asyncio.Semaphore(_MAX_CONCURRENT_JOBS=2)` — 초과 job은 `PENDING`으로 대기 |
| Job 상태 | 인메모리 `ProfilerService._jobs`(폴링용 캐시, 재시작 시 소실) — 산출물은 DB에 있음 |

---

## 7. HTTP API

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/profiler/run` | 메인 파이프라인 job 시작 (202) |
| `GET` | `/api/v1/profiler/jobs/{job_id}` | job 상태·프로필 결과·알림 |
| `GET` | `/api/v1/profiler/me/profile` | 최신 `user_profile_history` |
| `GET` | `/api/v1/profiler/me/analyses` | 분석 목록 (완료 스냅샷 + 진행 중 job) |
| `GET` | `/api/v1/profiler/me/analyses/compare?from=&to=` | 두 스냅샷 비교 (compare 서브에이전트) |
| `GET` | `/api/v1/profiler/me/analyses/{snapshot_id}` | 스냅샷 단건 |
| `DELETE` | `/api/v1/profiler/me/analyses/{snapshot_id}` | 스냅샷 삭제 (+dedup 소스 삭제 → 같은 파일 재분석 가능) |
| `DELETE` | `/api/v1/profiler/me/analyses/batch/{batch_id}` | 진행 중 배치 취소 |
| `DELETE` | `/api/v1/profiler/me/analyses/source/{source_id}` | 진행 중 단일 소스 취소 |
| `GET` | `/api/v1/profiler/profile/{user_id}` | 최신 (user_id 지정) |
| `POST` | `/api/v1/profiler/video-summary/run` | 서브그래프만 (`limit` optional, 202) |
| `GET` | `/api/v1/profiler/video-summary/{task_id}` | 영상 분석 단독 task 상태 |

**응답 스키마:** `schemas/profiler/http/snapshot.py::DbProfileResponse` — `snapshot_id`, 21축 점수, `portrait`, `top_categories`, `top_channels`(+`_long`/`_short`), `tone_of_user`, `dominant_traits`, `behavior_reasoning`, `supporting_evidence` 등.

---

## 8. DB · 디렉터리

| 테이블 | 쓰기 | 읽기 |
|--------|------|------|
| `user_watch_catalog` | Indexer | `profiler_repository.fetch_catalog_rows`·`fetch_catalog_signal_rows` 등 |
| `video_analysis` | `store` | `build_profile`, `fetch_unanalyzed_catalog` |
| `user_profile_history` | `build_profile` | `GET /me/profile`, 분석 목록/단건 |

`user_profile_history` 신규 컬럼: `portrait`(JSONB, §4b), `batch_id`(FK→`analysis_batch`, 유발 배치 박제). **트랜잭션:** 레포는 flush/execute, commit은 노드·API에서.

```text
backend/app/
  agents/profiler/
    facade.py · graph.py · prompts.py · llm.py · semantics.py · axis_labels.py · habit_metrics.py
    nodes/ video_summary.py · build_profile.py · notify.py
    sub_agent/video_summary/ (graph · prompts · nodes: select/summarize/embed/store)
    sub_agent/compare/       (graph · nodes · prompts · state · utils)
    state/profiler.py
  agents/shared/ embedding.py · persona.py · analysis_window.py(WATCH_CATALOG_WINDOW_DAYS)
  services/profiler/ service.py(Job·세마포어) · portrait.py(초상 생성) · sampling.py · scores.py
  repositories/profiler_repository.py
  api/v1/profiler.py · schemas/profiler/ (http/ · llm/ · job.py)
```

---

## 9. 알려진 제약

- **진행 상태·결과는 DB 영속**: running/completed/failed·`stage`는 `user_analysis_source`, 프로필은 `user_profile_history`. 분석 목록은 DB만 읽어 재시작에 안전.
- **크래시로 중단된 소스는 고아화**: 실행 중 프로세스가 죽으면 `user_analysis_source`가 `running`인 채 남아 화면에 "분류/분석 중"이 계속 표시됨(자동 reconcile 없음).
- Resend rate limit 시 메일은 조용히 `sent=False`.
