# Navigator Agent — 아키텍처 최종 결정서

> 브랜치: `navigator/test`  
> 작성일: 2026-06-08  
> 결정자: 진성 (Navigator 담당)  
> 상태: **✅ 확정**

---

## 결정 요약

**Dual-Layer Navigator (제안 3)** 채택.

```
Layer A  Profiler 8각   행동 측정 (WHAT)   ← Profiler 팀이 산출
    +
Layer B  인지주권 4지수  파생 해석 (HOW)    ← Navigator 팀이 파생
    =
12차원 이상향 추론
```

---

## 왜 이 구조인가

| 검토안 | 탈락 이유 |
|--------|-----------|
| 제안 1 Profiler-Native | Navigator 고유 가치(버블 탈출 유도) 희석 |
| 제안 2 Unified 재설계 | Profiler 팀과 스펙 전면 재합의 필요, 일정 리스크 |
| Layer B 6축 확장 시도 | 탐색넓이·깊이집중도가 Layer A와 신호 중복, 직관성 저하 |
| **제안 3 Dual-Layer** | **✅ 각 팀 독립 개발 + 인지주권 개념 UI에 살아있음** |

---

## Layer A — Profiler 8각 (행동 측정)

> Profiler v1.0 스펙 그대로. Navigator는 이 값을 **읽기만** 한다.

| # | UI 라벨 | key | 정의 |
|---|---------|-----|------|
| 1 | 지적 호기심 | `intellectual_curiosity` | 새 채널·낯선 주제 넓게 탐색 |
| 2 | 자기계발 | `self_improvement` | 습관·목표·생산성 콘텐츠 |
| 3 | 사회·시선 | `social_awareness` | 뉴스·다큐·이슈 관심량 |
| 4 | 깊이·몰입 | `depth_immersion` | 장편·연속·한 주제 집중 |
| 5 | 실용 지향 | `practical_orientation` | 튜토리얼·How-to·스킬 |
| 6 | 정서·위로 | `emotional_comfort` | ASMR·힐링·스트레스 해소 |
| 7 | 창의·표현 | `creative_expression` | DIY·메이킹·창작 |
| 8 | 오락·해방 | `entertainment_release` | 예능·밈·가벼운 엔터 |

### Layer A 보조 KPI (Profiler 산출)

```json
{
  "meta": {
    "profile_polarization": 42,
    "profile_balance": 58,
    "dominant_axes": ["practical_orientation", "entertainment_release"],
    "weak_axes": ["creative_expression", "social_awareness"]
  },
  "auxiliary": {
    "consumption_concentration": 0.71,
    "echo_chamber_risk": 0.58,
    "search_active_ratio": 0.31
  }
}
```

---

## Layer B — 인지주권 4지수 (파생 해석)

> Navigator가 Layer A + Layer 3 보조 KPI를 입력받아 **파생 계산**한다.  
> 직접 측정값이 아님 — UI 면책 문구 필요.

### 4지수 정의

#### 1. 관점 균형 지수 `perspective_balance`

```
= 100 - normalize( std([intellectual_curiosity, social_awareness,
                         practical_orientation, emotional_comfort]) )
```

- **의미**: 프로필 전체의 편중 정도. 특정 성향에 쏠려있을수록 낮음
- **낮으면**: 필터버블 진입 경보 → Navigator OPPOSITE 이상향 우선 제안
- **신호 출처**: Layer A 4개 축 분산 계산

#### 2. 주체성 지수 `autonomy_index`

```
= search_active_ratio × 100
```

- **의미**: 알고리즘 추천 의존 vs 직접 검색·탐색 비율
- **낮으면**: 추천 피드 의존도 높음 → 오늘의 퀘스트 1순위 타깃
- **신호 출처**: Layer 3 `search_active_ratio`

#### 3. 탐색 넓이 `exploration_width`

```
= intellectual_curiosity × 0.7 + len(weak_axes) × 10
```

- **의미**: 현재 탐색 중인 지식 공간의 넓이
- **낮으면**: ADJACENT 이상향에서 인접 분야 확장 방향 강화
- **신호 출처**: Layer A `intellectual_curiosity` + Layer 2 `weak_axes` 수

#### 4. 성장 잠재력 `growth_potential`

```
= self_improvement × 0.6 + depth_immersion × 0.4
```

- **의미**: 단기 성장 가속도. 자기계발 관심 + 깊이 있는 학습 태도
- **낮으면**: 자기계발 콘텐츠 + 장편 시청 루틴 퀘스트 생성
- **신호 출처**: Layer A `self_improvement` + `depth_immersion`

---

## 12차원 이상향 추론 흐름

```
NavigatorInput {
    # Layer A — 행동 성향 (8차원)
    profiler_axes: {
        intellectual_curiosity: 72,
        self_improvement:       65,
        social_awareness:       35,   ← weak
        depth_immersion:        40,
        practical_orientation:  78,   ← dominant
        emotional_comfort:      55,
        creative_expression:    28,   ← weak
        entertainment_release:  62,
    },

    # Layer A 메타
    dominant_axes: ["practical_orientation", "entertainment_release"],
    weak_axes:     ["creative_expression", "social_awareness"],

    # Layer B — 인지주권 (4차원)
    navigator_indices: {
        perspective_balance: 52,
        autonomy_index:      31,   ← 최우선 개선
        exploration_width:   70,
        growth_potential:    55,
    },
}
```

### 이상향 추론 규칙

| 이상향 타입 | 추론 방식 |
|-------------|-----------|
| **OPPOSITE** | `dominant_axes` → -30~-40점 / `weak_axes` → +25~+35점 / Layer B 전체 +20점 |
| **ADJACENT** | `weak_axes` → +15~+20점 / `dominant_axes` → -5~-10점 / Layer B → +10~+20점 |
| **BALANCED** | Layer A 모든 축 → 50±15 수렴 / Layer B 모든 지수 → 65 이상 목표 |

---

## Profiler 팀 협의 요청 사항

> 경준에게 전달 — Navigator가 12차원 추론을 위해 필요한 필드

| 필드 | 현재 스펙 포함? | 요청 내용 |
|------|----------------|-----------|
| `dominant_axes` | ✅ Layer 2 포함 | 그대로 유지 |
| `weak_axes` | ✅ Layer 2 포함 | 그대로 유지 |
| `search_active_ratio` | ✅ Layer 3 포함 | 그대로 유지 |
| `echo_chamber_risk` | ✅ Layer 3 포함 | 그대로 유지 |
| 축별 점수 0~100 | ✅ 포함 | 그대로 유지 |

**결론: Profiler 스펙 변경 없이 Navigator 독립 개발 가능.**

---

## UI 표현 가이드

### 메인 화면
```
[Profiler 8각 레이더 차트]   ← Layer A
  현재 프로필 (파란 실선)
  이상향 프로필 (빨간 점선)

[인지주권 4지수 게이지]       ← Layer B
  관점 균형  ████████░░  52
  주체성     ████░░░░░░  31  ← 경고색
  탐색 넓이  ███████░░░  70
  성장 잠재력 █████░░░░░  55

[이상향 선택 버튼]
  반대형 / 인접형(추천) / 균형형
```

### Layer B 면책 문구 (필수)
```
인지주권 4지수는 YouTube 시청·검색 패턴에서 파생된 참고 지표입니다.
직접 측정값이 아니며, 미디어 이해도·비판적 사고를 직접 평가하지 않습니다.
```

---

## Navigator Agent 구현 매핑

| 기능 | 입력 | 출력 |
|------|------|------|
| `design_ideal_auto()` | `current_radar` (Layer A) | 3가지 이상향 제안 |
| `generate_guide()` | `comparison` (12차원 gap) | 30일 로드맵 |
| `generate_quests()` | `comparison` + `top5_interests` | 오늘의 퀘스트 3개 |
| `build_playlist()` | `selected_ideal` + `top5_interests` | YouTube 큐레이션 |
| `chat()` | `state` + `user_message` | SSE 스트리밍 응답 |

### Layer B 파생 계산 시점

```python
# Profiler 데이터 수신 후 Navigator가 즉시 계산
def compute_layer_b(profiler_data: dict) -> NavigatorIndices:
    axes      = profiler_data["axes"]
    meta      = profiler_data["meta"]
    auxiliary = profiler_data["auxiliary"]

    perspective_balance = 100 - normalize(
        std([axes["intellectual_curiosity"],
             axes["social_awareness"],
             axes["practical_orientation"],
             axes["emotional_comfort"]])
    )
    autonomy_index    = auxiliary["search_active_ratio"] * 100
    exploration_width = axes["intellectual_curiosity"] * 0.7 \
                      + len(meta["weak_axes"]) * 10
    growth_potential  = axes["self_improvement"] * 0.6 \
                      + axes["depth_immersion"] * 0.4

    return NavigatorIndices(
        perspective_balance = round(clamp(perspective_balance), 1),
        autonomy_index      = round(clamp(autonomy_index), 1),
        exploration_width   = round(clamp(exploration_width), 1),
        growth_potential    = round(clamp(growth_potential), 1),
    )
```

---

## 개발 로드맵

```
Phase 1 (현재 navigator/test)
  ✅ schemas.py    — 8각 RadarChart + IdealRadarChart 모델
  ✅ state.py      — LangGraph NavigatorState
  ✅ prompt.py     — 6종 프롬프트
  ✅ tool.py       — 이상향 수식 자동생성 + 가이드/퀘스트
  ✅ graph.py      — LangGraph 8단계 워크플로우
  ✅ base.py       — NavigatorAgent 진입점
  ✅ youtube.py    — YouTube API
  ✅ api/v1/navigator.py — FastAPI 라우터

  🔲 Layer B 파생 계산 함수 추가 (compute_layer_b)
  🔲 NavigatorState에 navigator_indices 필드 추가
  🔲 Profiler 연동 테스트 (mock 데이터로 우선)

Phase 2 (dev 브랜치 머지 후)
  🔲 Profiler API 실제 연동
  🔲 DB 모델 (RadarChart, IdealRadarChart, Quest 저장)
  🔲 Frontend 8각 + 4지수 차트 컴포넌트 연동

Phase 3 (v2.0)
  🔲 Layer B 신호 정밀화 (Indexer 완주율 데이터 수신 후)
  🔲 이상향 추론 LLM 보강
  🔲 Spotify·뉴스 확장 시 Layer A 축 재검토
```

---

## 한 줄 요약

```
Layer A(Profiler·8각·행동) + Layer B(Navigator·4지수·인지) = 12차원 이상향 설계
```

---

*검토 필요 시: Navigator 진성 / Profiler 경준 스펙 회의 요청*
