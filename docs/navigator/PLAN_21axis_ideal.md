# Navigator 이상향 21축화 계획 (13축 설계 → 8축 파생, 에이전트 자체 구현)

> 목표: 이상향을 "현재 13축 기반으로 이상향 13축(반대/심화/균형) 설계 → 8축은 거기서 파생"
> 구조로 전환하고, **현재 vs 이상향**을 21축 전부 시각화한다.
> 원칙: **프로파일러와 공유하지 않고 네비게이터 안에 스키마·로직을 자체 구현**한다.

## 핵심 설계 결정

1. **생성 방향 전환 (13 → 8)**
   - 지금: LLM이 현재 21축을 근거로 **이상향 8축만 직접 출력**(13축은 참고용, 출력 안 함).
   - 변경: LLM이 **이상향 13축(가치관10+기질3)을 직접 설계** → 그 13축에서 **네비게이터 자체 매핑**으로 이상향 8축 파생.
   - 효과: 8축이 13축에서 나오므로 8/13 정합, 사장님 멘탈 모델과 일치, 13축 비교 가능.

2. **프로파일러와 분리 (자체 구현)** — *이전 "behavior_mapping 추출/공유" 계획 폐기*
   - 네비게이터가 **자체 13축 스키마 + 자체 derive 함수**를 가진다. profiler의 `ValuesTemperamentOutput`/`rule_based_behavior_spider`를 **import 하지 않음**.
   - 근거: ① 스키마가 이미 에이전트별 분리 ② 의도가 다름(프로파일러=관찰 추론, 네비게이터=설계 타깃) ③ 결합 시 프로파일러 리팩터가 네비게이터를 깰 위험.
   - **공유 일관성 이득 없음**: 프로파일러의 현재 8축은 순수 규칙이 아니라 LLM 블렌드(0.8)+캘리브레이션 결과라 `rule_based_behavior_spider(현재13)`과 이미 다름. 따라서 매핑을 공유해도 "현재8 vs 이상향8 동일 기반"은 성립 안 함 → 분리해도 손해 없음.
   - **순수 상수(축 한글 라벨 `SCORE_LABELS_KO`)는 공유 가능** — 로직이 아니라 표기라 결합 위험 낮음(현재도 navigator가 재사용 중).

3. **저장**: `user_ideal_persona`에 `values_temperament` **JSONB 1컬럼** 추가(13축). 8축은 기존 컬럼 유지.

4. **채팅 세부조정도 13축 기준**: interpret가 13축을 조정 → 8축 파생. `event: ideal`이 8축+13축 함께 스트리밍 → 레이더(8)·바(13) 동시 실시간 갱신.

## 백엔드 변경 (모두 `agents/navigator/` 내부)

### 에이전트
- [ ] `schemas.py`:
  - 신규 `IdealValuesDesign(BaseModel)` = **네비게이터 자체 13축**(values10+temperament3) + `persona_label` + `reasoning` — LLM 출력 스키마. (profiler 스키마 import 안 함)
  - `IdealRadar`(8축)는 유지.
  - 신규 내부 묶음 `ProposedIdeal{ideal_type, scores8, values13, persona_label, reasoning}`.
  - `IdealAdjustment`를 13축 조정 기반으로 (`updated_design: IdealValuesDesign`).
- [ ] `behavior_map.py` (신규, 네비게이터 자체):
  - `BEHAVIOR_SOURCE_WEIGHTS` 가중치 테이블(자체 보유) + `derive_8_from_13(values13) -> dict[str,float]` (clamp 포함).
  - 프로파일러와 동일 수식으로 시작하되 **독립 소유** (이후 자유롭게 튜닝).
- [ ] `ideal.py`:
  - `_propose_one`: LLM → `IdealValuesDesign` → `derive_8_from_13` → `ProposedIdeal` 반환.
  - `propose_ideals` 반환 타입 `list[ProposedIdeal]`.
  - `persona_label_from_scores` 유지(폴백).
- [ ] `prompts/propose.py`: "8축 출력" → **"이상향 13축 출력"**. 각 타입(반대/심화/균형) 의도를 13축 기준으로 서술.
- [ ] `prompts/chat.py`: interpret를 "13축 조정"으로.
- [ ] `nodes/interpret.py`: 13축 조정 → 8축 파생, `event: ideal` 콘텐츠를 `{behavior:8, values_temperament:13}` JSON으로 확장.
- [ ] `base.py`(파사드): propose/derive/persona_label 노출 정리.

### 레이어 (service/repo/schema/api/model)
- [ ] `models/user_ideal_persona.py`: `values_temperament: Mapped[dict|None]` (JSONB).
- [ ] `alembic/versions/011_navigator_ideal_values.py`: 컬럼 추가 (revision id ≤32자 주의).
- [ ] `repositories/navigator_repository.py`: `create_ideal`에 `values_temperament` 저장.
- [ ] `schemas/navigator.py`:
  - `ValuesTemperament13`(or dict) 응답 모델.
  - `ProposalItem`/`IdealResponse`에 `values_temperament` 추가.
  - `ComparisonResponse`에 현재/이상향 13축 동봉.
  - `ConfirmIdealRequest`에 `values_temperament` 추가.
- [ ] `services/navigator/service.py`:
  - `get_proposals`: ProposedIdeal → ProposalItem(8+13+persona+reasoning).
  - `confirm_ideal`: 13축 저장.
  - `get_comparison`: 현재 13축(스냅샷 scores에서 추출) + 이상향 13축 동봉.
  - `_ideal_to_response`: 13축 포함.

## 프론트 변경
- [ ] `lib/ideals/api.ts`: `ProposalItem`/`IdealResponse`/`ComparisonResponse`에 `values_temperament`; `createIdeal`에 동봉; `streamChat` onIdeal가 `{behavior, values_temperament}` 파싱.
- [ ] 신규 `components/ideals/CompareBars.tsx`: 현재 vs 이상향 막대 비교(현재=muted, 이상향=primary). 라벨맵(`VALUES_AXES`/temperament) 재사용.
- [ ] `IdealSetupPage` RefineChat: 8축 아래 현재-단독 바 → **현재 vs 이상향 비교 바**로 교체, event:ideal로 실시간 갱신.
- [ ] 제안 카드(펼침): 8축 레이더 + 13축 비교 바(선택).
- [ ] `IdealDetailPage`: 비교 섹션에 13축 현재 vs 이상향 추가.

## 마이그레이션/검증
- [ ] alembic 011 (dev 컨테이너는 `docker cp` 후 `alembic upgrade head` — [[dev-alembic-not-mounted]]).
- [ ] ruff + import + tsc.
- [ ] 라이브: 제안 13축 생성·8축 파생, 채팅 13축 실시간, 확정 저장/조회.

## 리스크 / 메모
- **프로파일러 무수정** — 이번 변경은 전부 navigator 내부 + navigator 레이어. (프로파일러는 안 건드림)
- **8축이 규칙 파생**으로 바뀜(현재는 LLM 직접). 의도된 변경(8/13 정합). 필요 시 추후 블렌딩.
- **가중치 중복**(navigator 자체 보유) — 의도된 독립. 프로파일러 튜닝과 자동 동기화 안 됨(허용).
- **레거시 이상향**(values_temperament=NULL): 13축 비교는 빈 값 → 8축만 표시(graceful). 신규부터 21축.
- `event: ideal` 콘텐츠 형식 변경 → 프론트 onIdeal 동시 수정 필수.
- 13축 미저장(현재 프로필) 결정과 무충돌: 이건 **이상향 타깃 13축**(새 데이터)이라 별개.
