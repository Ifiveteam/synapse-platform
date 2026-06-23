# Navigator 제안 3안 캐싱 계획

> 문제: `GET /navigator/proposals`가 매 방문마다 LLM 3콜을 새로 돌려
> ① 비용·지연 ② **3안이 매번 바뀜(일관성 깨짐)** — 나갔다 들어오면 다른 추천.
> 목표: (유저 + 분석 스냅샷)별로 제안 3안을 캐시해 재사용 + 수동 "다시 추천".

## 테이블이 필요한가? → 예 (전용 테이블)

- 영속·세션무관·재현 가능한 캐시는 새 테이블이 정석.
- 기존 테이블 재사용 불가: `user_profile_history`(프로파일러 소유 → 경계 위반),
  `user_ideal_persona`(확정 이상향용 → 개념 혼합·목록 오염).
- 가벼운 대안(프론트 sessionStorage)은 세션·기기 넘으면 소실 → 비권장.

## 캐시 키 / 무효화

- **키 = (user_id, source_profile_history_id)** — 같은 분석이면 입력(21축) 고정 → 제안 고정.
- **결정: refresh 허용 (하드락 X).** 기본은 캐시 고정 → "같은 스냅샷 = 같은 3안"이 보장되되,
  사용자가 **`?refresh=true` / "다시 추천"** 으로 새로 뽑으면 캐시를 덮어쓴다. (즉 "refresh 전까지 고정")
- 자동 재생성은 안 함(비용). (선택) `catalog_count` 저장 → 시청기록 많이 늘면 "새로 추천 권장" 힌트만.

## 패턴: 가이드 캐시(guide_json)와 동일

이미 검증된 guide 캐시와 같은 결로 간다 (저위험).

## 백엔드 변경 (전부 navigator 레이어)

- [ ] **모델** `models/navigator_proposal_cache.py`:
  `NavigatorProposalCache(id, user_id FK CASCADE, source_profile_history_id FK SET NULL,
  proposals_json JSONB, generated_at, catalog_count)` + **UNIQUE(user_id, source_profile_history_id)**.
- [ ] **마이그레이션** `012_navigator_proposal_cache.py` (revision id ≤32자).
- [ ] **레포** `navigator_repository.py`:
  - `get_proposal_cache(user_id, snapshot_id) -> row | None`
  - `save_proposal_cache(user_id, snapshot_id, proposals_json, catalog_count)` (upsert on conflict).
- [ ] **서비스** `get_proposals(user_id, source_profile_history_id=None, refresh=False)`:
  - 스냅샷 id 확정(없으면 `_load_profile_or_404`가 주는 row.id = 최신 스냅샷).
  - refresh 아니고 캐시 있으면 → **캐시 그대로 반환**(LLM 안 돔).
  - 아니면 `agent.propose` → ProposalItem 직렬화(JSON) 저장 → 반환.
  - 캐시 JSON ↔ ProposalsResponse 변환은 pydantic `model_dump`/`model_validate`.
- [ ] **엔드포인트** `GET /proposals`에 `refresh: bool = Query(False)` 추가.
- [ ] (선택) `ProposalsResponse`에 `generated_at`/`stale` 추가 — "다시 추천" 힌트용.

## 프론트 변경

- [ ] `lib/ideals/api.ts`: `getProposals(snapshotId?, refresh?)` 에 refresh 파라미터.
- [ ] `IdealSetupPage` ShowProposals: **"다시 추천" 버튼** → `getProposals(id, true)` 재요청.
- [ ] (선택) 생성 시각 표시 + stale 배너(시청기록 늘었을 때).

## 동작/주의

- **캐싱 ≠ 저장**: 3안은 확정 전 후보. 확정한 것만 `user_ideal_persona`로 간다(별개).
- 제안 JSON은 현재 shape(13축+8축+persona+reasoning) 그대로 저장 → 읽을 때 그대로 반환.
- 스냅샷별 캐시라, 분석 버전을 바꾸면(Step1) 그 스냅샷의 캐시를 따로 사용/생성.
- 마이그레이션은 dev 컨테이너에 `docker cp` 후 `alembic upgrade head` ([[dev-alembic-not-mounted]]).

## 검증

- ruff + import + tsc.
- 라이브: 첫 호출 생성·저장 → 2번째 호출 **동일 3안 즉시 반환(LLM 미호출, 빠름)** → `refresh=true` 시 새 3안.
