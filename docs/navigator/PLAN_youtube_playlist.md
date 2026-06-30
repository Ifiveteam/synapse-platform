# Navigator 이상향 기반 YouTube 재생목록 계획

> 상태: 설계 확정 + **백엔드 Phase A 구현 완료**(2026-06-25). 전체 설계·현황은 [PLAN.md](./PLAN.md).
> 범위: 익스텐션 YouTube 2갈래(① 재생목록, ② DOM 자동화 시청) 중 **① 재생목록**.
> ② DOM 자동화 시청은 익스텐션 기반 별개 작업(이 문서 밖).

## 0. 구현 현황 (2026-06-25)
| 단계 | 내용 | 상태 |
|---|---|---|
| ① | DB 모델 `navigator_playlist` + 마이그레이션 002 | ✅ (라운드트립 검증) |
| ② | `youtube_client.py` (search?type=channel · RSS) | ✅ |
| ③ | 에이전트 스키마 (PlaylistItem·Playlist·QuerySpec·ChannelPick·PlaylistCuration·EditSpec) | ✅ |
| ④ | 서브에이전트 생성루프(discover→pick→collect→evaluate→curate) + 파사드 `generate_playlist` + repo store(grounding/watched) | ✅ (실 DB 생성 검증) |
| ⑤ | 레포 CRUD (create·list·get·update·rename·delete) | ✅ |
| ⑥ | HTTP DTO + 서비스(create·list·get·rename·delete) + API 5엔드포인트 | ✅ (서비스 E2E 검증) |
| ⑦ | 프론트 (Phase A: 진입 버튼·목록·생성·카드) | ⬜ |
| ⑧ | 영상별 새로고침 (A2) | ⬜ |
| ⑨ | 채팅 부분수정 (A3, SSE) | ⬜ |
| ⑩ | 실제 YouTube 저장 (Phase B) | ⬜ |

검증 스크립트: `scripts/navigator_youtube_playlist_verify.py`(서브에이전트), `scripts/navigator_playlist_crud_verify.py`(CRUD 서비스).
미결: `summary` 컬럼 유지/제거 (§3 참고).

## 1. 한 줄 정의
적용/선택한 **이상향(13축 페르소나)** + **사용자 시청 기록(카테고리·채널·영상)** 을 근거로 YouTube 영상 **10개**를 추천하고, 사용자가 **영상별 새로고침 / 채팅**으로 다듬은 뒤 **본인 YouTube 계정에 실제 재생목록으로 저장**한다. **이상향 1개에 재생목록 여러 개**(개수 무제한, 추후 결제 플랜별 차등 여지) 생성 가능.

**진입 UX**: 이상향 상세 페이지(`IdealDetailPage`)에 **[재생목록 추천] 버튼** → 그 이상향의 재생목록 뷰(목록 + 생성)로 진입.

## 2. 사용자 시나리오
```
① 이상향 선택 상태에서 [재생목록 생성] 버튼 → 영상 10개 추천 (썸네일·제목·채널·추천이유)
   (여러 번 누르면 재생목록이 여러 개 쌓임 → 목록에서 관리)
② 마음에 안 드는 영상 → 카드의 [새로고침] → 그 자리만 다른 영상으로 교체
③ 채팅 → "경제는 빼고 과학 위주로" → 1~2개만 부분 수정 (SSE 실시간)
④ [내 유튜브에 저장] → 실제 재생목록 생성 (youtube 권한 1회 동의)
```

## 3. 데이터 모델 — 새 테이블 `navigator_playlist` (1 이상향 : N 재생목록)

> 가이드(1:1)는 `user_ideal_persona.guide_json` 컬럼이면 됐지만, 재생목록은 **이상향당 여러 개**라 별도 테이블이 필요하다. 이상향 자체(유저당 N개)와 같은 엔티티 패턴.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | UUID PK | 재생목록 식별자 |
| `user_id` | UUID FK users CASCADE | |
| `ideal_id` | UUID FK user_ideal_persona CASCADE | 어느 이상향의 재생목록인지 (출처 추적은 이걸로 충분) |
| `title` | Text | 자동 `{persona_label} #N`(순번), **사용자 수정 가능** |
| `summary` | Text | 재생목록 총평(LLM 큐레이션). ⚠️ 유지/제거 미정 |
| `items_json` | JSONB | 보여줄 영상 10개 |
| `channels_json` | JSONB | 발굴·선택한 채널 목록 `{channel_id, title}` — re-RSS로 무쿼터 보충 |
| `reservoir_json` | JSONB | 미리 뽑아둔 여분 영상(즉시 교체용) |
| `youtube_playlist_id` | Text\|None | 실제 저장 후 채워짐(Phase B) |
| `created_at` / `updated_at` | TimestampMixin | |

- 인덱스: `(user_id, ideal_id)`.
- **새 테이블은 이거 하나.** catalog 근거(카테고리·채널·시청영상)·watched 디덥은 **기존 `user_watch_catalog`에서 읽기만** 한다.
- 테이블 `navigator_playlist`은 **`001_initial_schema`에 포함**(통합 스키마)되어 있음 — 별도 마이그레이션 파일 없음.

## 4. 추천 근거 — 이상향(13축) + 시청 기록 둘 다

추천은 이상향만 보지 않고 **사용자가 실제로 쌓은 것**을 근거로 삼는다:
- **이상향**: `persona_label` + 13축 `values_temperament` + `reasoning` + `ideal_type` (8축은 파생물이라 직접 안 씀).
- **시청 기록(catalog grounding)**: 상위 카테고리 + 상위 채널 + **대표 시청영상 제목 샘플** (`indexer_repository` + `user_watch_catalog`).

들어가는 3 지점:
```
① 검색어 작문 : 이상향 + 시청근거 → 검색어 (예: 게임 즐겨보는 분석형 → "게임 데이터 분석", "e스포츠 전략 해설")
② 큐레이션    : 후보 채널/영상 선택 시 친숙도(적재 채널·카테고리)와 이상향 부합도 함께 고려
③ watched 디덥: 이미 본 영상 제외
```

## 5. 채널 발굴 — `search?type=channel` (스파이크로 확정)
```
LLM 검색어 작문 → search?type=channel&maxResults=25 (1콜=실재 채널 25개, 100유닛)
   → LLM 큐레이션(실재 후보 중 선택) → 채널 RSS(무료) → 안 본 새 영상 → 10개 + 저수지
```
- ❌ LLM이 채널 핸들/URL 직접 주는 무쿼터 경로는 스파이크 실패(정확도 ~2/10·오결). ✅ `type=channel` 검색이 실재 channelId 보증(환각 0).

## 6. 에이전트 — `sub_agent/youtube/` (가이드 sub-agent 동형 + human-in-the-loop)
```
[생성 루프]  discover(검색어→search) → pick(채널선택) → collect(RSS) → evaluate(자기교정) → curate(10개+이유)
[편집 루프]  interpret(요청해석) → (필요시 discover) → curate(부분수정)   ← 사람이 루프 재진입
```
- 자기교정: 후보 부족 시 검색어 넓혀 재발굴(상한 `MAX_ATTEMPTS`).
- 편집: 같은 노드를 사람 입력으로 재진입. **보충 우선순위 ① `reservoir`(즉시) → ② `channels_json` re-RSS(무료) → ③ 검색(100유닛, 새 주제만)**. **부분 수정(1~2개만, 나머지 유지)**.
- store 주입(가이드 패턴): service가 `store=self.repo` → 노드가 catalog 근거·watched·검색을 store로.

## 7. API (navigator 라우터, 리소스 중심)

| Method | Path | 용도 | 비고 |
|---|---|---|---|
| POST | `/ideal/{ideal_id}/playlists` | 새 재생목록 **생성**(sub-agent 실행) | 버튼=생성, 새 행 |
| GET | `/ideal/{ideal_id}/playlists` | 그 이상향의 재생목록 **목록** | 요약 |
| GET | `/playlists/{playlist_id}` | 단건 조회 | |
| PATCH | `/playlists/{playlist_id}` | 제목 수정(`{title}`) | 사용자 rename |
| DELETE | `/playlists/{playlist_id}` | 삭제 | |
| POST | `/playlists/{playlist_id}/item/refresh` | 영상 1개 교체(`{video_id}`) | 저수지 우선 |
| POST | `/playlists/{playlist_id}/chat` (SSE) | 채팅 부분수정(`{message}`) | status/playlist 이벤트 |
| POST | `/playlists/{playlist_id}/save` | 실제 YouTube 저장 | youtube 쓰기 스코프 |

## 8. 단계 & 쿼터

| 단계 | 내용 | OAuth | YouTube 쿼터 |
|---|---|---|---|
| **A** | 생성 + 목록/조회 | 무변경 | 100~200유닛/생성(버튼당) |
| **A2** | 영상별 새로고침 | 무변경 | ~0 (저수지→채널 re-RSS 무료) |
| **A3** | 채팅 부분수정(SSE) | 무변경 | ~0, 새 주제일 때만 100 |
| **B** | 실제 저장 | youtube 쓰기 **1회 동의** | 550유닛/저장(50 + 50×10) |

- A는 OAuth 무변경. B만 `youtube` 쓰기 스코프 → 풀 재로그인 아니라 **1회 권한 동의**(기존 토큰 소급 불가). 기본 스코프에 넣으면 신규 유저 자동.

## 9. 구현 (파일)

### 백엔드
- `agents/navigator/sub_agent/youtube/`
  - `youtube_client.py` — **유튜브 호출 IO 헬퍼**(코드가 부르는 것, tool 아님): `search_channels`(type=channel) · `fetch_channel_uploads`(RSS) · `create_playlist`/`add_playlist_item`(Phase B)
  - `constants.py` · `store.py`(Protocol: catalog 근거·watched·검색) · `state.py` · `prompts.py`
  > `tools/`(LLM 자율 함수호출 자리)는 안 씀 — 검색 횟수=쿼터를 코드가 통제해야 하므로 youtube IO는 **코드 호출 헬퍼**. LLM은 검색어·선택만 출력.
  - `nodes/` — `discover` · `pick` · `collect` · `evaluate` · `curate` · `interpret`(편집)
  - `graph.py` — 생성 그래프 + 편집 그래프(노드 공유), `run_playlist` / `edit_playlist`
- `agents/navigator/schemas.py` — `PlaylistItem`·`Playlist`·`QuerySpec`·`ChannelPick`·`PlaylistCuration`·`EditSpec`
- `agents/navigator/base.py` — 파사드 `generate_playlist` / `edit_playlist` / `refresh_item`(store 주입)
- `models/navigator_playlist.py` (테이블은 `001_initial_schema`에 통합)
- `repositories/navigator_repository.py` — CRUD(`create_playlist`/`list_playlists`/`get_playlist`/`update_playlist`/`delete_playlist`) + catalog 근거 조회 + `fetch_watched_video_ids`
- `schemas/navigator.py` — `PlaylistItemResponse`·`PlaylistResponse`·`PlaylistSummary`·`SavePlaylistResponse`
- `services/navigator/service.py` — `create_playlist`·`list_playlists`·`get_playlist`·`rename_playlist`·`delete_playlist`·`refresh_item`·`chat_edit`(SSE)·`save_to_youtube`
- `api/v1/navigator.py` — §7 엔드포인트 **추가**(가이드 sub-agent처럼 navigator 라우터에). 새 라우터 파일·`__init__.py` 변경 없음. (너무 커지면 추후 navigator 라우터의 **하위 라우터**로 분리, sibling 아님)
- (Phase B) `services/google_oauth.py` — `SCOPES`에 youtube 추가

### 프론트
- `lib/ideals/api.ts` — `createPlaylist`·`listPlaylists`·`getPlaylist`·`renamePlaylist`·`deletePlaylist`·`refreshPlaylistItem`·`streamPlaylistChat`(SSE)·`savePlaylistToYoutube`
- `pages/IdealDetailPage.tsx` — **[재생목록 추천] 진입 버튼**
- 재생목록 뷰(이상향 하위, 라우트 `/me/ideals/:id/playlists` 또는 상세 내 섹션) — 목록 + [생성] + 카드(썸네일·제목·채널·이유) + 카드별 [새로고침] + 채팅 입력(SSE) + 제목 수정(rename) + [내 유튜브에 저장]
- (선택) `components/ideals/PlaylistCard.tsx`

## 10. 검증

| # | 항목 |
|---|---|
| 0 ✅ | 스파이크 — `type=channel` 1콜=실재 채널 25개(RSS 8/8 활동), LLM 직접 식별자 경로 실패 확인 → 검색 방식 확정 |
| 1 | 서브에이전트 실검증 — `scripts/navigator_youtube_playlist_verify.py`: 실 store 주입 생성. 실재 video_id·채널, watched 제외, 10개+저수지, 자기교정 루프, catalog 근거 반영, 편집(새로고침·채팅 부분수정) |
| 2 | HTTP E2E(A) — 생성 → 목록 → 단건 → 새로고침 → 채팅 |
| 3 | HTTP E2E(B) — youtube 동의 후 저장 → 실제 재생목록·`youtube_playlist_id` |
| 4 | 마이그레이션 — `alembic upgrade head` ↔ `downgrade -1` (테이블 생성/삭제) |
| 5 | 프론트 — `pnpm build` + 수동(생성·목록·새로고침·채팅·저장) |

## 11. 리스크 / 하지 말 것
- **검색어 품질(주 리스크)**: 부적절하면 후보가 어긋남 → evaluate가 검색어 넓혀 재발굴(`MAX_ATTEMPTS` 한도). 후보는 항상 실재(`type=channel`)라 환각 없음.
- **자기교정/편집 루프 상한 필수**: `MAX_ATTEMPTS` 가드(=검색 콜 폭주 방지). evaluate는 규칙 기반(LLM 0콜).
- **환각 id 방지**: LLM은 검색어·인덱스·이유만, channel_id/video_id는 search/RSS가 소유.
- **쓰기 쿼터(B)**: 10개 ≈ 550유닛/저장. 사용자 트리거 1회, 증액으로 완화.
- **하지 말 것**: LLM 채널 핸들/URL 신뢰(스파이크 실패), 8축 단독 타깃(이상향=13축), 무가드 루프, 백그라운드 사전생성. Phase A/B 독립 출시 유지.

## 12. 다음 단계 (이 문서 밖)
- ② 익스텐션 YouTube DOM 자동화 시청(알고리즘 형성) — 익스텐션 기반 별개.
- (옵션) Phase B 저장을 ②의 익스텐션 DOM으로 대체 시 쓰기 쿼터 0 가능.
