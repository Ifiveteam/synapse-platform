# Navigator Agent — 아키텍처 최종 결정서

> 브랜치: `navigator/test`  
> 작성일: 2026-06-08  
> 결정자: 진성 (Navigator 담당)  
> 상태: **✅ 확정 (v1.1 반영)**

---

## 결정 요약

**Dual-Layer Navigator (제안 3)** 채택.

```
Layer A  Profiler 8각      행동 측정 (WHAT)      ← Profiler 산출
    +
Layer B  인지주권 4지표     소비 습관 (HOW)       ← Profiler 산출
    =
12차원 이상향 추론          ← Navigator 전담
```

**역할 분리 원칙 (v1.1)**

- 측정·분석은 **Profiler 전부** (Layer A + Layer B).
- **Navigator는 Profiler JSON을 읽기만** — 파생 지수 재계산 없음.
- 이상향은 동일 key에 목표값만 설계.

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

> Profiler v1.1 스펙 그대로. Navigator는 이 값을 **읽기만** 한다.  
> 범위: 0~100 (높을수록 해당 성향 강함)

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

---

## Layer B — 인지주권 4지표 (소비 습관)

> **Profiler v1.1 산출** — Navigator는 읽기만 한다.  
> 직접 측정값이 아님 — UI 면책 문구 필요.

| # | UI 라벨 | key | 범위 | 방향 | 한 줄 정의 |
|---|---------|-----|------|------|------------|
| 1 | 주체성 | `search_active_ratio` | 0~1 | 높을수록 좋음 ✅ | 직접 검색·탐색 vs 추천·습관 소비 |
| 2 | 채널 편중도 | `viewing_concentration` | 0~1 | **높을수록 나쁨** ⚠️ | 시청이 소수 채널에 몰리는 정도 |
| 3 | 취향 다양성 | `taste_diversity_index` | 0~100 | 높을수록 좋음 ✅ | 취향 4종(지적·사회·실용·정서) 분산 |
| 4 | 탐색 깊이 | `exploration_depth` | 0~1 | 높을수록 좋음 ✅ | 새 주제 진입 시 얼마나 깊게 보는가 |

> **주의:** `viewing_concentration`만 방향이 반대입니다.  
> UI 게이지 색상: 높을수록 빨강 / Navigator 이상향: 낮추는 방향으로 설계.

### Layer B 면책 문구 (필수)

```
인지주권 4지표는 YouTube 시청·검색 패턴에서 파생된 참고 지표입니다.
미디어 이해도·비판적 사고·정치적 동조를 직접 평가하지 않습니다.
```

---

## JSON 계약 (v1.1)

```json
{
  "user_id": "mock_jiyeon",
  "computed_at": "2026-06-08T09:00:00Z",

  "layer_a": {
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

  "top5_interests": ["IT", "운동", "요리", "독서", "여행"],
  "summary": "실용 지향 중심의 습관형 소비 패턴. 추천 의존도 높음."
}
```

---

## 8축 이중 방향 (OPPOSITE + EXPANSION)

> **설계 원칙:** 모든 축에 반대(OPPOSITE)와 확장(EXPANSION) 방향을 모두 정의한다.  
> Navigator는 유저 needs·Layer B 신호에 따라 **축별로 방향을 선택**하여 이상향을 생성한다.

| 축 | OPPOSITE (반대 방향) | EXPANSION (확장 방향) |
|----|---------------------|----------------------|
| **지적 호기심** | 한 주제 깊은 몰입<br>→ `depth_immersion` ↑ | 타문화·이종학문으로 더 넓게<br>→ `social_awareness` ↑ |
| **자기계발** | 무목적 여유·놀이 소비<br>→ `entertainment_release` ↑ | 철학적 성찰·삶의 의미 탐구<br>→ `depth_immersion` ↑ |
| **사회·시선** | 내면·솔로·명상 콘텐츠<br>→ `emotional_comfort` ↑ | 글로벌 시각·다문화 이해<br>→ `intellectual_curiosity` ↑ |
| **깊이·몰입** | 가볍고 다양한 탐색<br>→ `entertainment_release` ↑ | 전문가·학문적 깊이<br>→ `self_improvement` ↑ |
| **실용 지향** | 순수 성찰·인문학<br>→ `intellectual_curiosity` ↑ | 고급 스킬·전문 기술 마스터리<br>→ `self_improvement` ↑ |
| **정서·위로** | 도전·비판·불편한 진실<br>→ `self_improvement` ↑ | 다양한 감정 스펙트럼·예술<br>→ `creative_expression` ↑ |
| **창의·표현** | 수용·감상·분석 위주<br>→ `intellectual_curiosity` ↑ | 다른 매체·협업 창작<br>→ `social_awareness` ↑ |
| **오락·해방** | 깊이·집중·진지한 콘텐츠<br>→ `depth_immersion` ↑ | 다양한 장르·문화 오락<br>→ `social_awareness` ↑ |

### 3단계 강도 (α)

| 단계 | α | OPPOSITE 체감 | EXPANSION 체감 |
|------|---|--------------|----------------|
| Level 1 | 0.25 | 거부감 없이 받아들이는 반대 | 조금 더 넓게 |
| Level 2 | 0.55 | 약간의 불편함이 있는 반대 | 인접 분야까지 |
| Level 3 | 1.00 | 완전히 다른 형태·많이 불편한 반대 | 새 영역 개척 |

### Navigator 방향 선택 기준

| Layer B 신호 | 우선 추천 방향 |
|-------------|--------------|
| `viewing_concentration` 높음 (편중) | dominant 축 → **OPPOSITE** |
| `search_active_ratio` 낮음 (추천 의존) | 모든 축 → **OPPOSITE** Level 1 우선 |
| `exploration_depth` 낮음 (얕게 훑음) | weak 축 → **EXPANSION** Level 1 |
| `taste_diversity_index` 낮음 (쏠림) | weak 축 → **OPPOSITE** + **EXPANSION** 혼합 |
| 유저 명시적 선택 | 선택 방향 우선 (추론 override) |

---

## 12차원 이상향 추론 흐름

```
ProfilerResult (layer_a + layer_b)
    ↓
[Navigator 전처리]
  dominant_axes = layer_a 상위 2개 (점수 차 ≥ 15 기준)
  weak_axes     = layer_a 하위 2개 (점수 차 ≥ 15 기준)
    ↓
[방향 선택] 축별로 OPPOSITE / EXPANSION 결정
    ↓
[강도 선택] α = 0.25 / 0.55 / 1.00
    ↓
[이상향 3종 생성]
  OPPOSITE  — dominant 축 반대 방향 (Level 2~3)
  EXPANSION — weak 축 확장 방향 (Level 1~2)
  BALANCED  — 전 축 50±15 수렴 + Layer B 전체 개선
    ↓
[이상향 layer_b 목표]
  search_active_ratio    ↑ 높이기
  viewing_concentration  ↓ 낮추기  ← 방향 반전 주의
  taste_diversity_index  ↑ 높이기
  exploration_depth      ↑ 높이기
```

### 이상향 입력 예시

```json
{
  "layer_a": {
    "intellectual_curiosity": 72,
    "self_improvement": 65,
    "social_awareness": 35,
    "depth_immersion": 40,
    "practical_orientation": 78,
    "emotional_comfort": 55,
    "creative_expression": 28,
    "entertainment_release": 62
  },
  "dominant_axes": ["practical_orientation", "entertainment_release"],
  "weak_axes": ["creative_expression", "social_awareness"],
  "layer_b": {
    "search_active_ratio": 0.31,
    "viewing_concentration": 0.71,
    "taste_diversity_index": 52,
    "exploration_depth": 0.44
  }
}
```

---

## UI 표현 가이드

### 메인 화면

```
[Profiler 8각 레이더 차트]   ← Layer A
  현재 프로필 (파란 실선)
  이상향 프로필 (빨간 점선)

[인지주권 4지표 게이지]       ← Layer B
  주체성       ████░░░░░░  0.31  ← 경고색 (낮음)
  채널 편중도  ████████░░  0.71  ← 경고색 (높을수록 나쁨 ⚠️)
  취향 다양성  █████░░░░░  52    ← 경고색 (낮음)
  탐색 깊이    ████░░░░░░  0.44

[이상향 선택 버튼]
  반대형 / 확장형 / 균형형
```

### Layer B 게이지 색상 규칙

| 지표 | 경고 조건 |
|------|---------|
| `search_active_ratio` | < 0.4 → amber |
| `viewing_concentration` | **> 0.6 → amber** (방향 반전) |
| `taste_diversity_index` | < 50 → amber |
| `exploration_depth` | < 0.4 → amber |

---

## Navigator Agent 구현 매핑

| 기능 | 입력 | 출력 |
|------|------|------|
| `design_ideal_auto()` | `layer_a` + `layer_b` | 3가지 이상향 (OPPOSITE/EXPANSION/BALANCED) |
| `generate_guide()` | `comparison` (12차원 gap) | 30일 로드맵 |
| `generate_quests()` | `comparison` + `top5_interests` | 오늘의 퀘스트 3개 |
| `build_playlist()` | `selected_ideal` + `top5_interests` | YouTube 큐레이션 |
| `chat()` | `state` + `user_message` | SSE 스트리밍 응답 |

---

## 개발 로드맵

```
Phase 1 (navigator/test)
  ✅ schemas.py    — 8각 RadarChart + IdealRadarChart 모델
  ✅ state.py      — LangGraph NavigatorState
  ✅ prompt.py     — 6종 프롬프트
  ✅ tool.py       — 이상향 수식 자동생성 + 가이드/퀘스트
  ✅ graph.py      — LangGraph 8단계 워크플로우
  ✅ base.py       — NavigatorAgent 진입점
  ✅ api/v1/navigator.py — FastAPI 라우터
  ✅ Frontend Navigator 페이지 (8각 차트 + 4지표 게이지 + 이상향 선택 + 가이드/퀘스트)

  🔲 v1.1 스펙 반영 — schemas/tool/api layer_a·layer_b 구조 교체
  🔲 8축 이중 방향(OPPOSITE+EXPANSION) 구현
  🔲 dominant/weak 임계값(≥15) 적용
  🔲 viewing_concentration 방향 반전 처리

Phase 2 (dev 브랜치 머지 후)
  🔲 Profiler API 실제 연동
  🔲 DB 모델 (RadarChart, IdealRadarChart, Quest 저장)
  🔲 Frontend mock → 실제 API 연결

Phase 3 (v2.0)
  🔲 Navigator 방향 추론 LLM 보강 (Layer B → 축별 방향 자동 결정)
  🔲 Indexer 완주율 데이터 수신 후 Layer B 정밀화
  🔲 Spotify·뉴스 확장 시 Layer A 축 재검토
```

---

## 변경 이력

| 버전 | 내용 |
|------|------|
| v1.0 | Dual-Layer Navigator 구조 확정 |
| v1.1 | Profiler v1.1 반영 — Layer B Profiler 통합, 4지표 교체<br>8축 이중 방향(OPPOSITE+EXPANSION) 설계 확정<br>`viewing_concentration` 방향 반전 명시 |

---

## 한 줄 요약

```
Profiler(Layer A 8각 + Layer B 4지표) → Navigator(읽고, 축별 반대·확장 방향 선택, 이상향 설계)
```

---

*검토 필요 시: Navigator 진성 / Profiler 경준 스펙 회의 요청*
