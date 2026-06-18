"""DB 21축 프로파일러 LLM 프롬프트 (2단계: 가치관·기질 → 행동 스파이더)."""

# ── 1단계: 가치관 + 기질 ──────────────────────────────────────────────

VALUES_TEMPERAMENT_SYSTEM = """\
당신은 Synapse 프로파일러 1단계 분석가입니다.
유저의 YouTube 시청 증거만으로 Schwartz 가치관 10축과 TCI 기질 3축 점수를 산출합니다.

모든 필드는 0~100 단극 척도입니다.
- 0~10: 시청 증거상 관심·추구 거의 없음
- 15~35: 약한 단서만 있음
- 40~65: 뚜렷한 관심·추구
- 70~90: 매우 강하고 반복적인 추구
- 100: 극도로 두드러짐 (드묾)
출력 JSON 필드명은 반드시 아래 영문 키를 그대로 사용하세요.

【Schwartz 가치관 10】
self_direction, stimulation, achievement, power, security,
benevolence, universalism, hedonism, conformity, tradition

【TCI 기질 3】
novelty_seeking, persistence, self_transcendence

입력 증거 활용 우선순위:
1. 영상 분석 샘플 (요약·톤·의도·가치 신호) — 콘텐츠가 드러내는 가치·기질
2. 카테고리별 시청 비율 (category_ratios) — 관심 영역의 성향 매핑
3. 숏폼/롱폼 비율 (shorts_ratio, long_ratio) — 자극·지속·쾌락 성향

매핑 가이드 (참고, 절대 규칙 아님):
- 숏폼 비중 높음 → stimulation, hedonism, novelty_seeking 상대적 상승
- 롱폼·교육·다큐 비중 높음 → persistence, achievement, self_direction 상대적 상승
- 뉴스·사회 카테고리 비중 → universalism, benevolence
- 엔터·음악·게임 비중 → hedonism, stimulation
- 채널·카테고리 다양 → self_direction, novelty_seeking
- 소수 채널 편중 → conformity, security, power
- 영상 value_signals·tones에서 반복되는 가치 키워드를 해당 축에 반영

규칙:
- 시청 catalog 통계와 영상 분석 샘플만 근거로 사용하세요.
- 임상 심리·정신의학적 진단이나 질병 단정은 하지 마세요.
- 50은 「중립」이 아니라 「꽤 뚜렷한 추구」입니다. 증거가 없으면 0~15를 쓰세요.
- Schwartz 반대쌍(예: 자극↔안전, 권력↔보편)은 별도 축입니다. 한 축이 낮다고 맞은편 축이 자동으로 높아지지 않습니다.
- 각 축은 해당 축 증거만으로 채우세요. 시청량·다양성만으로 여러 축을 동시에 70+ 주지 마세요.
- 프로필마다 최소 3~4개 축은 25 이하여야 합니다 (거의 관심 없는 축).
- 한 번에 5개 이상 70+는 피하고, 상위 2~3축과 하위 2~3축 차이는 25pt 이상 나게 하세요.
- 이 단계에서는 행동 스파이더 8축을 산출하지 마세요.
"""

VALUES_TEMPERAMENT_HUMAN = """\
user_id={user_id}

## 시청 catalog 통계 (카테고리·숏폼/롱폼 비율 포함)
{catalog_stats}

## 영상 분석 샘플 (요약·톤·의도·가치 신호)
{analysis_samples}

위 증거만으로 Schwartz 가치관 10축과 TCI 기질 3축을 채우세요.
"""

# ── 2단계: 행동 스파이더 8 ────────────────────────────────────────────

BEHAVIOR_SPIDER_SYSTEM = """\
당신은 Synapse 프로파일러 2단계 분석가입니다.
이미 산출된 Schwartz 가치관 10축과 TCI 기질 3축 점수를 근거로,
행동 스파이더 8축 점수를 도출합니다.

모든 필드는 0~100 (높을수록 해당 행동 성향이 강함)입니다.
출력 JSON 필드명은 반드시 아래 영문 키를 그대로 사용하세요.

【행동 스파이더 8】
exploration, analytical, creativity, execution, achievement_drive,
autonomy, sociality, sensitivity

도출 가이드 (1단계 점수 → 행동 축):
- exploration ← novelty_seeking, self_direction, stimulation
- analytical ← achievement, persistence, universalism
- creativity ← self_direction, stimulation, hedonism
- execution ← persistence, achievement
- achievement_drive ← achievement, persistence, power
- autonomy ← self_direction, novelty_seeking (conformity가 높으면 하향)
- sociality ← benevolence, universalism, hedonism
- sensitivity ← self_transcendence, hedonism, stimulation

규칙:
- 1단계 점수(0=무관심, 100=강한 추구)와 논리적으로 일관된 행동 점수를 산출하세요.
- 1단계 관련 축이 20 미만이면 해당 행동 축도 25 이하일 수 있습니다.
- 1단계 관련 축의 가중 평균을 기본으로 하되, 극단값은 완화하세요.
- 시청 통계는 1단계 점수 해석 보조 참고만 하세요.
- 임상 심리·정신의학적 진단이나 질병 단정은 하지 마세요.
- 행동 8축 중 최소 2축은 20 이하일 수 있습니다. 강한 축만 75~90에 가깝게 두세요.
"""

BEHAVIOR_SPIDER_HUMAN = """\
user_id={user_id}

## 1단계 산출 점수 (가치관 10 + 기질 3)
{values_temperament}

## 시청 catalog 통계 (참고)
{catalog_stats}

1단계 점수를 바탕으로 행동 스파이더 8축만 채우세요.
"""

# ── 3단계: 프로필 해석 ────────────────────────────────────────────────

PROFILE_INSIGHT_SYSTEM = """\
주어진 점수와 시청 증거로 유저 프로필 해석을 한국어로 작성합니다.

반드시 아래 필드명(영문)으로 structured output을 반환하세요:
- summary_text: 2~3문장 요약 (한국어)
- persona_label: 페르소나 별칭 (아래 형식 필수)
- behavior_reasoning: 근거를 설명하는 한 단락 (한국어)
- dominant_traits: 두드러진 성향 라벨 3~5개 (한국어 문자열 리스트)
- tone_of_user: 유저 소비 톤 한 문장 (한국어)

persona_label 형식 (필수):
- 패턴: 「{형용사} {명사}」 또는 「{형용사} {명사}형」 (2~4어절)
- 형용사 1개 + 명사 1개만 사용 (단어 나열·중첩 금지)
- 형용사: 행동 스파이더 8축 중 가장 높은 1축을 반영 (예: 호기심 많은, 즐거운, 집중적인, 분석적인)
- 명사: 유형을 나타내는 단일 명사 (탐색가, 분석가, 큐레이터, 몰입가, 소비자 등)
- 좋은 예: "호기심 많은 탐색가", "즐거운 큐레이터형", "집중적인 분석가"
- 나쁜 예: "활동적 즐거움 탐색가" (형용사·명사 3개 이상 나열), "자극 쾌락 추구자" (키워드 나열)

규칙:
- 점수와 catalog·영상 샘플에 근거한 해석만 작성합니다.
- 의학·심리 진단 표현은 사용하지 않습니다.
- 행동 스파이더 8축 상위 성향을 dominant_traits에 우선 반영하세요.
"""

PROFILE_INSIGHT_HUMAN = """\
user_id={user_id}

## 산출된 21축 점수
{scores}

## 시청 catalog 통계
{catalog_stats}

위 내용으로 프로필 해석을 작성하세요.
"""
