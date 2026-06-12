# Synapse 8 — Profiler 스펙 (Layer A + Layer B)

> **버전:** v1.1  
> **일자:** 2026-06-08  
> **상태:** 확정 (팀 공유·구현 기준)  
> **구현:** [IMPLEMENTATION.md](./IMPLEMENTATION.md) (코드·API·마이그레이션)

YouTube 시청·검색 데이터로 사용자 **디지털 소비 프로필**을 산출합니다.

- **Layer A** — 8각 레이더 (콘텐츠 취향, WHAT)
- **Layer B** — 인지주권 4지표 (소비 습관, HOW)

---

## 1. 맥락

| 에이전트 | 역할 |
|----------|------|
| **Indexer** | Takeout 등 → `IndexedRecord[]` 저장 |
| **Profiler** | 기록 분석 → **Layer A + Layer B + TOP5 + 요약** |
| **Navigator** | Profiler JSON **읽기만** → 동일 key에 **이상향 목표 점수**·퀘스트 |

**역할 분리 원칙**

- **측정·분석은 Profiler 전부** (8각 + 인지주권 보조 4개).
- 예전 Layer 2 meta (`dominant_axes`, `profile_balance` 등)는 **API에 노출하지 않음** — 이상향 시 `axes`에서 즉시 계산.
- Navigator는 **파생 지수를 재계산하지 않음**.

---

## 2. 설계 원칙

1. **Layer A 8축 = 콘텐츠 취향** (무엇을·어떤 톤으로 소비하는가)
2. **편향·균형·주/공백 축** → 8각에 별도 축·API 필드로 두지 않음
3. **소비 습관·편중·탐색 방식** → **Layer B** (레이더 밖 게이지)
4. Layer A 점수 **0–100** (높을수록 해당 성향 **강함**)
5. LLM은 요약·보조; 축 점수 본체는 **행동 집계 + 분류**

### `depth_immersion` vs `exploration_depth`

| | Layer A `depth_immersion` | Layer B `exploration_depth` |
|--|---------------------------|------------------------------|
| 질문 | 평소 **장편·몰입** 성향? | **새로 탐색할 때** 얼마나 깊게? |
| UI | 레이더 축 | 보조 게이지 |

---

## 3. 출력 구조

```
ProfilerResult
├── axes                 # Layer A — 8각 (API 키, 문서상 layer_a)
├── layer_b              # 인지주권 4지표
├── top5_interests
├── summary
├── interpretation     # §9 해석 4요소
└── (선택) axis_notes, computed_at, user_id
```

**UI**

```
[Layer A] 8각 레이더     — "어떤 콘텐츠 취향인가"
[Layer B] 게이지 4개     — "인지주권 · 소비 습관"
[Navigator] 이상향 점선  — axes·layer_b 와 동일 key
```

---

## 4. Layer A — 8각 (`axes`)

**의미:** 무엇을·어떤 톤으로 소비하는가  
**범위:** 0~100

| # | UI 라벨 | key | 정의 | 주요 신호 |
|---|---------|-----|------|-----------|
| 1 | 지적 호기심 | `intellectual_curiosity` | 새 지식·낯선 주제·채널 **넓게** 탐색 | 신규 채널/주제, 검색 다양도 |
| 2 | 자기계발 | `self_improvement` | 습관·목표·생산성 | 자기계발, 루틴 태그 |
| 3 | 사회·시선 | `social_awareness` | 타인·세상·이슈 **관심량** | 뉴스, 토크, 다큐 |
| 4 | 깊이·몰입 | `depth_immersion` | **길게·연속·한 주제 깊게** | 장편 비율, 시청 길이, binge, Shorts 역가중 |
| 5 | 실용 지향 | `practical_orientation` | 문제 해결·스킬·How-to | 튜토리얼, 검색 의도 |
| 6 | 정서·위로 | `emotional_comfort` | 힐링·감성·스트레스 해소 | ASMR, 음악, 위로형 |
| 7 | 창의·표현 | `creative_expression` | 만들기·실험·예술 | DIY, 메이킹, 창작 |
| 8 | 오락·해방 | `entertainment_release` | 가볍·해방적 소비 | 예능, 밈, 엔터 |

### 축 구분 (참고)

| | A | B |
|--|---|---|
| 넓이 vs 깊이 (성향) | 1 지적 호기심 | 4 깊이·몰입 |
| 톤 vs 몰입 | 6 오락·해방 | 4 깊이·몰입 |
| 관심량 vs 채널 편중 | 3 사회·시선 | `viewing_concentration` |

### Navigator 축 타입 (이상향 규칙 — Navigator 소유)

| 타입 | 해당 축 | 이상향 방향 |
|------|---------|-------------|
| GROWTH | 지적호기심, 자기계발, 사회·시선 | 높은 방향 |
| EXPANSION | 깊이·몰입, 창의·표현 | 인접 확장 |
| FLEXIBLE | 실용, 정서, 오락 | dominant↓ / weak↑ / 중립→50 |

### 점수 산출 (개념)

```text
axis_score = normalize( Σ (tag_weight × exposure) + behavior_features )
```

**깊이·몰입 참고**

```text
depth_immersion =
  w1 · long_form_ratio
+ w2 · avg_watch_duration_norm
+ w3 · binge_series_score
+ w4 · topic_depth_concentration
− w5 · shorts_ratio
→ 0–100
```

---

## 5. Layer B — 인지주권 4지표 (`layer_b`)

**의미:** 8각으로 부족한 **소비 습관·편중·탐색 방식**  
**산출:** Profiler

| # | UI 라벨 | key | 범위 | 한 줄 정의 |
|---|---------|-----|------|------------|
| 1 | 주체성 | `search_active_ratio` | 0~1 | 직접 검색·탐색 vs 추천·습관 소비 |
| 2 | 채널 편중도 | `viewing_concentration` | 0~1 | 시청이 소수 채널에 몰리는 정도 |
| 3 | 취향 다양성 | `taste_diversity_index` | 0~100 | 취향 4종(지적·사회·실용·정서) 분산 |
| 4 | 탐색 깊이 | `exploration_depth` | 0~1 | 새 주제·신규 채널 진입 시 **얼마나 깊게** 보는가 |

### 5.1 네 지표가 묻는 질문

| key | 질문 |
|-----|------|
| `search_active_ratio` | **어떻게** 고르는가 |
| `viewing_concentration` | **어디서** 보는가 |
| `taste_diversity_index` | **무엇을** 골고루 보는가 |
| `exploration_depth` | **새로 볼 때 얼마나 깊게** 보는가 |

### 5.2 측정 신호

| key | 신호 |
|-----|------|
| `search_active_ratio` | `search` record 수 / 전체 record 수 |
| `viewing_concentration` | top 채널 시청 시간 비율 + 채널 수 보정 |
| `taste_diversity_index` | `100 - norm(std([intellectual_curiosity, social_awareness, practical_orientation, emotional_comfort]))` |
| `exploration_depth` | 탐색 시청 subset — 아래 수식 |

### 5.3 `exploration_depth` 수식 (MVP — C안)

**시드:** 각 `source_type: search` 기록  
**트레일:** 검색 직후 **첫 watch**의 `channel`을 anchor로, 이후 **같은 channel** watch만 이어 붙임.

**연장 규칙:** 트레일 내 **마지막 시청 시각 기준 24시간** 이내면 계속, 초과 시 트레일 종료.

```text
per_search_thread_score =
  0.6 × norm(트레일 총 duration_sec, 1200)
+ 0.4 × norm(트레일 편수, 5)

exploration_depth = mean(per_search_thread_score for each search)
→ clamp(0, 1)
```

| 조건 | 값 |
|------|-----|
| 검색 0건 | `0.0` |
| 검색만 있고 watch 없음 | 해당 시드 thread = `0` |
| v1.2 | tags/query 기반 확장 (MVP는 **같은 channel만**) |

| 값 | 의미 |
|----|------|
| 높음 (≥ 0.6) | 검색 후 **같은 채널**로 오래·연속 시청 |
| 중간 (0.35~0.6) | 보통 |
| 낮음 (< 0.35) | 검색 후 **얕게** 훑거나 트레일이 짧음 |

### 5.4 UI 카피 예

| key | 낮을 때 | 높을 때 |
|-----|---------|---------|
| 주체성 | 추천·습관에 맡기는 비중이 큼 | 직접 찾아보는 비중이 큼 |
| 채널 편중도 | 채널이 고르게 분산 | 소수 채널에 시청 집중 |
| 취향 다양성 | 특정 취향에 쏠림 | 취향이 고르게 분산 |
| 탐색 깊이 | 새 콘텐츠를 얕게 훑음 | 새 주제를 깊게·이어서 탐색 |

### 5.5 v1.0 → v1.1 폐기·통합

| v1.0 (폐기) | v1.1 (Layer B) |
|-------------|----------------|
| `profile_polarization`, `profile_balance` | `taste_diversity_index` |
| `dominant_axes`, `weak_axes` | API 미노출 — Navigator가 `axes`에서 계산 |
| `consumption_concentration`, `echo_chamber_risk` | `viewing_concentration` |
| `shorts_ratio` | `exploration_depth` |
| `exploration_width`, `growth_orientation`, `autonomy_index` | 제거 (중복) |
| Navigator Layer B 파생 계산 | Profiler로 통합 |

---

## 6. JSON 계약

```json
{
  "user_id": "mock_jiyeon",
  "computed_at": "2026-06-08T09:00:00Z",
  "axes": {
    "intellectual_curiosity": 72,
    "self_improvement": 65,
    "social_awareness": 35,
    "depth_immersion": 40,
    "practical_orientation": 78,
    "emotional_comfort": 55,
    "creative_expression": 28,
    "entertainment_release": 62
  },
  "layer_b": {
    "search_active_ratio": 0.31,
    "viewing_concentration": 0.71,
    "taste_diversity_index": 52,
    "exploration_depth": 0.44
  },
  "top5_interests": [],
  "summary": "...",
  "interpretation": {
    "consumption_mode": "탐색형",
    "primary_lever": "주체성",
    "sovereignty_verdict": "양호",
    "radar_gap_insight": "지적 호기심 점수는 높지만 탐색 깊이가 낮아..."
  }
}
```

---

## 7. Navigator 연동

1. Profiler JSON 수신 (`axes`, `layer_b`, `top5_interests`, `summary`).
2. **이상향 axes:** OPPOSITE / ADJACENT / BALANCED — 축 타입은 Navigator 상수.
3. **dominant / weak:** `axes` 점수 상·하위 1~2개 — Profiler 필드 불필요.
4. **이상향 layer_b:** 동일 key 목표값 (주체성↑, 편중도↓, 탐색깊이↑, 취향다양성↑).
5. 퀘스트·가이드·플레이리스트는 gap 기반.

---

## 8. Indexer ↔ Profiler 계약

| Indexer | Profiler |
|---------|----------|
| Taxonomy 태그 | Layer A 8축 가중 합산 |
| 시청 길이, Shorts 여부 | `depth_immersion`, `exploration_depth` |
| 채널·검색 메타 | Layer B habits |
| (선택) 완주율 | `depth_immersion` 보정 |

| Layer B 지표 | 필요 필드 |
|-------------|-----------|
| 주체성 | `source_type: search` |
| 채널 편중도 | `channel`, `duration_sec` (watch) |
| 탐색 깊이 | `channel`, `duration_sec`, `recorded_at`, `tags` |
| 취향 다양성 | Layer A 산출 후 내부 계산 |

---

## 9. (선택) 해석 결과 4요소

지표 숫자 보완용 — Profiler 규칙 기반 산출.

| key | UI | 설명 |
|-----|-----|------|
| `consumption_mode` | 소비 모드 | 습관형·탐색형·편향형 등 |
| `primary_lever` | 우선 개선 | 4지표 중 1순위 개입 포인트 |
| `sovereignty_verdict` | 종합 판정 | 양호 / 주의 / 개선 권장 |
| `radar_gap_insight` | 괴리 인사이트 | axes vs layer_b 불일치 1줄 |

---

## 10. UI 면책

**Layer A**

> Synapse 8은 YouTube 시청·검색 패턴 기반 **취향 요약**입니다.  
> 미디어 이해도·비판적 사고를 직접 측정하지 않습니다.

**Layer B**

> 인지주권 4지표는 시청·검색 패턴에서 파생된 **참고 지표**입니다.  
> 미디어 이해도·비판적 사고·정치적 동조를 **직접 평가하지 않습니다**.

---

## 11. 한 줄 요약

```text
Profiler = Layer A(8각) + Layer B(주체성·채널편중·취향다양성·탐색깊이) + TOP5 + 요약
Navigator = 읽고, 같은 key에 이상향만 설계
```

---

## 변경 이력

| 버전 | 내용 |
|------|------|
| v1.0 | 8축 확정. Layer 2 meta + Layer 3 auxiliary |
| v1.1 | Layer B 4지표 통합. meta API 제거. 탐색 깊이 확정. LAYER_AB_FINAL 본 문서에 병합 |
