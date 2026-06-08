# Synapse 8각 축 스펙 통합 제안서 v1.0

> Navigator(진성) × Profiler(경준) 충돌 분석 → 3가지 통합 방향 제안  
> 브랜치: `navigator/test` | 작성일: 2026-06-08

---

## 충돌 지점 분석

### 현재 스펙 비교표

| # | Navigator 현행 | Profiler v1.0 | 충돌 여부 |
|---|----------------|---------------|-----------|
| 1 | 관점 균형 (성장축) | — (메타 KPI로 이동) | ⚠️ **구조 충돌** |
| 2 | 주체성 (성장축) | — (Layer 3 search_active_ratio) | ⚠️ **위치 충돌** |
| 3 | 탐색의 넓이 (확장축) | 지적 호기심 `intellectual_curiosity` | 🔶 **이름만 다름** |
| 4 | 몰입의 깊이 (확장축) | 깊이·몰입 `depth_immersion` | ✅ **완전 일치** |
| 5 | 정서↔도전 (스펙트럼) | 정서·위로 + 오락·해방으로 분리 | ⚠️ **분해 충돌** |
| 6 | 실용↔성찰 (스펙트럼) | 실용 지향 `practical_orientation` | 🔶 **절반만 일치** |
| 7 | 개인↔사회 (스펙트럼) | 사회·시선 `social_awareness` | 🔶 **절반만 일치** |
| 8 | 소비↔창조 (스펙트럼) | 창의·표현 `creative_expression` | 🔶 **절반만 일치** |
| — | —             | 자기계발 `self_improvement`     | ❌ **Navigator 없음** |

### 핵심 충돌 요약

**1. 관점 균형 / 주체성의 위치 문제**
- Navigator: 8각 안에 두고 "높을수록 좋다" (성장축)
- Profiler: 편향·균형은 8각 형태 전체에서 파생 (Layer 2 메타 KPI)
- **문제:** Profiler가 `관점_균형=30` 을 산출할 방법이 없음. 행동 데이터로 직접 측정 불가.

**2. 스펙트럼 vs 단방향 성향**
- Navigator: 정서↔도전을 스펙트럼(양극) 하나의 축으로 봄
- Profiler: `emotional_comfort(40)` + `entertainment_release(70)` 처럼 각각 독립 측정
- **문제:** 같은 사람이 정서(60) + 도전(70) 둘 다 높을 수 있음. 스펙트럼으로 묶으면 정보 손실.

**3. 자기계발 축 누락**
- Profiler: `self_improvement` = Navigator가 핵심으로 다뤄야 할 축
- Navigator 현행에는 없음. 이상향 설계에서 가장 중요한 성장 방향인데 측정이 안 됨.

---

## 제안 1 — Profiler-Native (프로파일러 스펙 완전 채택)

> **"측정 가능성을 최우선으로. Navigator는 Profiler 데이터를 그대로 받아 해석만 한다."**

### 8각 축 (Profiler v1.0 그대로)

| # | UI 라벨 | key | 축 방향성 (Navigator용) |
|---|---------|-----|------------------------|
| 1 | 지적 호기심 | `intellectual_curiosity` | 높을수록 좋음 |
| 2 | 실용 지향 | `practical_orientation` | 반대=성찰/여유 |
| 3 | 정서·위로 | `emotional_comfort` | 반대=도전/불편 |
| 4 | 사회·시선 | `social_awareness` | 반대=내면/솔로 |
| 5 | 창의·표현 | `creative_expression` | 확장=다른 매체 |
| 6 | 오락·해방 | `entertainment_release` | 반대=깊이/집중 |
| 7 | 자기계발 | `self_improvement` | 높을수록 좋음 |
| 8 | 깊이·몰입 | `depth_immersion` | 확장=연속 시리즈 |

### Navigator 이상향 로직 (Profiler 데이터 기반)

```
입력: axes[8] + meta.dominant_axes + meta.weak_axes

OPPOSITE 이상향:
  dominant_axes의 반대 방향으로 -30 ~ -40점
  weak_axes는 +20 ~ +30점

ADJACENT 이상향:
  weak_axes에 +15 ~ +20점 (인접 확장)
  dominant_axes는 현재 유지 또는 -5점

BALANCED 이상향:
  모든 축을 50 ± 10 범위로 수렴
```

### 관점 균형 / 주체성 처리

```
관점_균형 → Layer 2: profile_balance (편중도 역수)
주체성   → Layer 3: search_active_ratio
→ 8각 차트 아래 "인지주권 지수" 별도 UI로 표시
```

### 장단점

| 장점 | 단점 |
|------|------|
| Profiler 연동 즉시 가능 | "관점 균형" UI에서 사라져 사용자 혼란 |
| 행동 측정 기반, 신뢰도 높음 | Navigator 핵심 가치(버블 탈출)가 약해짐 |
| 개발 공수 최소 | 스펙트럼 긴장감 없음 (단방향 성향만) |
| Profiler 스펙 변경 시 Navigator 자동 반영 | 8개 축이 시각적으로 "섞여" 보임 |

### 추천 대상
팀 일정이 빡빡하고, Profiler 연동을 최우선으로 할 때.

---

## 제안 2 — Synapse 8 Unified (통합 재설계)

> **"Profiler 측정 가능성 + Navigator 방향성을 동시에 만족하는 8개 축 재정의"**  
> 양 팀이 합의하여 하나의 공통 스펙을 만드는 방안.

### 8각 축 (재설계)

| # | UI 라벨 | key | 타입 | Profiler 측정 방법 | Navigator 방향 |
|---|---------|-----|------|--------------------|----------------|
| 1 | 지적 호기심 | `intellectual_curiosity` | 확장(C) | 신규 채널·주제 다양도 | 인접 학문 확장 |
| 2 | 자기계발 | `self_improvement` | 성장(A) | 자기계발 태그 비율, 루틴 콘텐츠 | 높을수록 좋음 |
| 3 | 사회·시선 | `social_awareness` | 성장(A) | 뉴스·다큐·시사 비율 | 높을수록 좋음 |
| 4 | 깊이·몰입 | `depth_immersion` | 확장(C) | 장편 비율·평균 시청 시간·binge | 심화 탐색 확장 |
| 5 | 정서 ↔ 도전 | `emotional_vs_challenge` | 스펙트럼(B) | emotional_comfort - entertainment_release 차이 | 치우침 반대 |
| 6 | 실용 ↔ 성찰 | `practical_vs_reflection` | 스펙트럼(B) | practical_orientation - (철학·인문 태그) | 치우침 반대 |
| 7 | 소비 ↔ 창조 | `consume_vs_create` | 스펙트럼(B) | creative_expression - passive_consumption | 치우침 반대 |
| 8 | 개인 ↔ 세계 | `individual_vs_world` | 스펙트럼(B) | individual hobby - social_awareness 균형 | 치우침 반대 |

### 핵심 변경점

**관점 균형 → Layer 2 메타 KPI 이동 (Profiler 설계 채택)**
```
profile_balance = 100 - normalize(std(axes[8]))
→ 8각 밖 "인지주권 지수" UI로 분리 표시
```

**주체성 → search_active_ratio (Layer 3) 이동**
```
search_active_ratio = 검색 후 시청 / 전체 시청
→ 대시보드 보조 지표
```

**스펙트럼 축 산출 방식**
```
emotional_vs_challenge =
  normalize(emotional_comfort_score - challenge_score)
  → 0: 순수 정서, 50: 균형, 100: 순수 도전
```

### Profiler 산출 인터페이스 (Profiler 팀과 협의 필요)

```json
{
  "axes": {
    "intellectual_curiosity": 72,
    "self_improvement": 60,
    "social_awareness": 55,
    "depth_immersion": 35,
    "emotional_vs_challenge": 30,
    "practical_vs_reflection": 75,
    "consume_vs_create": 20,
    "individual_vs_world": 40
  },
  "meta": {
    "profile_balance": 58,
    "profile_polarization": 42,
    "dominant_axes": ["intellectual_curiosity", "practical_vs_reflection"],
    "weak_axes": ["depth_immersion", "consume_vs_create"]
  }
}
```

### 장단점

| 장점 | 단점 |
|------|------|
| 측정 가능 + 방향성 동시 만족 | Profiler 팀과 스펙 재합의 필요 |
| 스펙트럼 축이 직관적 시각화 가능 | 스펙트럼 점수 산출 공식 설계 복잡 |
| 자기계발·사회시선이 성장축으로 명시 | 두 팀의 합의 공수 발생 |
| 관점 균형 UI에서 자연스럽게 분리 | 버전 마이그레이션 필요 |

### 추천 대상
진성-경준이 스펙 회의를 통해 **공통 표준**을 만들 수 있을 때.

---

## 제안 3 — Dual-Layer Navigator (이중 레이어 분리)

> **"Profiler는 행동 측정, Navigator는 인지 해석. 두 레이어를 합쳐 이상향 설계."**  
> 가장 아키텍처적으로 깔끔하지만 개발 공수가 가장 큼.

### 구조

```
┌─────────────────────────────────────────────┐
│  Layer A: Profiler 8각 (행동 측정)           │
│  intellectual_curiosity  self_improvement    │
│  practical_orientation   emotional_comfort   │
│  social_awareness        creative_expression │
│  entertainment_release   depth_immersion     │
└──────────────────┬──────────────────────────┘
                   │ Profiler 산출
                   ▼
┌─────────────────────────────────────────────┐
│  Layer B: Navigator 인지주권 4지수 (파생)    │
│                                             │
│  관점 균형 지수 = f(관련 Profiler 축 분산)  │
│  주체성 지수   = f(search_active_ratio)     │
│  탐색 넓이     = f(intellectual_curiosity)  │
│  성장 잠재력   = f(self_improvement)        │
└──────────────────┬──────────────────────────┘
                   │ Navigator 계산
                   ▼
┌─────────────────────────────────────────────┐
│  이상향 설계 Input                           │
│  Profiler 8각 + 인지주권 4지수 합산 12차원  │
│  → OPPOSITE / ADJACENT / BALANCED 추론      │
└─────────────────────────────────────────────┘
```

### Layer B: Navigator 인지주권 4지수 산출 공식

```python
# 관점 균형 지수 (Profiler 축 값들의 편중도 역수)
perspective_balance = 100 - normalize(
    std([intellectual_curiosity, social_awareness, 
         practical_orientation, emotional_comfort])
)

# 주체성 지수 (Layer 3 검색 활성도 기반)
autonomy_index = search_active_ratio * 100

# 탐색 넓이 (intellectual_curiosity + weak_axes 수)
exploration_index = (intellectual_curiosity * 0.7 + 
                     len(weak_axes) * 10)

# 성장 잠재력 (자기계발 + 깊이 몰입 합산)
growth_potential = (self_improvement * 0.6 + 
                    depth_immersion * 0.4)
```

### UI 표현

```
[메인 레이더] Profiler 8각 차트
  intellectual_curiosity | self_improvement | ...

[하단 인지주권 게이지 4개]
  관점 균형  ████████░░  78
  주체성    ██████░░░░  62
  탐색 넓이  ████░░░░░░  41
  성장 잠재력 ███████░░░  71

[이상향 설계 버튼] → Navigator가 12차원으로 추론
```

### 이상향 추론 입력

```python
NavigatorInput(
    # Profiler 8각
    profiler_axes={...},      # 8개 행동 성향 점수

    # Navigator 인지주권 4지수
    navigator_indices={
        "perspective_balance": 78,
        "autonomy": 62,
        "exploration_width": 41,
        "growth_potential": 71,
    },

    # 이상향 방향 추론
    # dominant = [entertainment_release, practical_orientation]
    # weak     = [depth_immersion, social_awareness]
)
```

### 장단점

| 장점 | 단점 |
|------|------|
| Profiler 스펙 변경해도 Navigator 레이어 독립 유지 | 개발 공수 가장 큼 |
| 관점균형·주체성 개념 UI에 살아있음 | 12차원 이상향 추론 로직 복잡 |
| 각 팀 독립적으로 개발 가능 | 사용자에게 설명하기 어려움 |
| 가장 정교한 이상향 추론 가능 | 첫 MVP에는 오버스펙 |

### 추천 대상
v2.0 이후, Profiler 데이터가 안정화되고 Navigator가 독립 서비스로 성장할 때.

---

## 최종 비교표

| 기준 | 제안 1 (Profiler-Native) | 제안 2 (Unified) | 제안 3 (Dual-Layer) |
|------|--------------------------|------------------|---------------------|
| **개발 속도** | ⭐⭐⭐ 빠름 | ⭐⭐ 중간 | ⭐ 느림 |
| **측정 신뢰도** | ⭐⭐⭐ 높음 | ⭐⭐⭐ 높음 | ⭐⭐ 중간 |
| **Navigator 방향성** | ⭐ 약함 | ⭐⭐⭐ 강함 | ⭐⭐⭐ 강함 |
| **UI 직관성** | ⭐⭐ 중간 | ⭐⭐⭐ 높음 | ⭐⭐ 중간 |
| **Profiler 협의 공수** | ⭐⭐⭐ 없음 | ⭐ 필요 | ⭐⭐ 소폭 필요 |
| **확장성** | ⭐⭐ 중간 | ⭐⭐ 중간 | ⭐⭐⭐ 높음 |
| **MVP 적합성** | ✅ | ✅ | ❌ |

---

## 권장 방향

### 🥇 단기 MVP → **제안 2 (Unified)** 목표, **제안 1**로 시작

```
Phase 1 (현재): 제안 1로 Profiler 연동 먼저 완성
  → Navigator가 Profiler 8각 그대로 받아서 이상향 추론

Phase 2 (v1.1): 제안 2로 스펙 정합
  → 진성-경준 스펙 회의 후 스펙트럼 축 통합
  → 자기계발·사회시선 성장축 승격

Phase 3 (v2.0): 제안 3 인지주권 레이어 추가
  → Navigator 독립 서비스화
```

### 즉시 합의 필요 사항 (경준에게 전달)

1. **스펙트럼 축 처리**: `emotional_comfort` + `entertainment_release` 를 Profiler가 따로 산출하면 Navigator가 두 값의 차로 스펙트럼 점수 계산 가능 여부 확인
2. **`search_active_ratio` 제공 가능 여부**: Indexer가 검색 이벤트를 잡을 수 있는지
3. **Layer 2 메타 KPI 제공 시점**: `dominant_axes` / `weak_axes` 를 Profiler가 같이 내려주면 Navigator 이상향 추론 품질 대폭 향상

---

*이 문서는 Navigator 진성 작성. 경준(Profiler), 프론트엔드 팀 리뷰 후 v1.1 확정 예정.*
