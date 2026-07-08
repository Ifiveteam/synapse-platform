# 분석 상세 페이지 큐레이터 연결 + 사이드바 채팅기록 → 분석 목록 전환

날짜: 2026-07-08

## 배경

메인 큐레이터(Home 화면, `/`)를 더 이상 주력 진입점으로 쓰지 않기로 했다. 대신 `/me/analyses/:id`(분석 상세 페이지) 하단의 채팅창을 실제 큐레이터로 쓰기로 한다. 이 채팅창은 현재 프론트 전용 스텁으로, 어떤 질문을 해도 "아직 백엔드가 연결되지 않았어요"라는 고정 문구만 반환한다.

동시에, 좌측 사이드바(`Sidebar.tsx`)의 "채팅 기록" 섹션(과거 큐레이터 세션 목록)도 더 이상 의미가 없으므로, 개인성향 분석 목록으로 교체한다.

## 목표

1. `/me/analyses/:id`에서 실제 큐레이터(`/api/v1/curator/stream`)와 대화할 수 있다.
2. Home(`/`) 화면은 레이아웃을 바꾸지 않되, 실제 전송(백엔드 호출)만 막는다.
3. 좌측 사이드바의 "채팅 기록"을 "개인성향 분석 목록"으로 바꿔서, 클릭하면 해당 분석 상세로 바로 이동한다.

## 비목표

- 큐레이터가 "지금 보고 있는 분석 내용"을 자동으로 인지해서 답변에 반영하는 것(컨텍스트 주입)은 이번 스코프 밖. 지금은 그냥 기존 큐레이터 세션을 분석 상세 페이지에서 이어가는 것까지만.
- 새로운 백엔드 API나 새로운 zustand 스토어를 만들지 않는다. 기존 `useChatStore`, `ChatMessages`, `CuratorInput`, `useSidebarStore.analyses`를 그대로 재사용한다.

## 변경 사항

### 1. `frontend/src/pages/AnalysisDetailPage.tsx`

- 로컬 스텁 채팅 상태(`ChatMessage` 타입, `messages`/`chatInput` state, `sendChat` 함수, 가짜 응답 텍스트)를 제거한다.
- 하단 채팅 UI(드래그로 높이 조절되는 패널 + 입력창)는 기존 `ChatMessages`, `CuratorInput` 컴포넌트로 교체한다. 두 컴포넌트 모두 `useStore` prop을 받도록 이미 만들어져 있으므로 기본값(`useChatStore`, Home과 동일한 세션)을 그대로 쓴다.
- 드래그 리사이즈 핸들·패널 높이 로직(`chatHeight`, `dragRef`, `startResize`)은 그대로 유지 — `ChatMessages`를 그 안에 렌더링하는 wrapper만 남긴다.
- `messages.length > 0` 조건은 `useChatStore`의 `messages`로 대체한다.

### 2. `frontend/src/components/home/curator-input.tsx`

- `offline?: boolean` prop 추가 (기본값 `false`).
- `offline`이 `true`면 기존 `disabled` 계산에 포함시켜(`disabled = !user || isStreaming || offline`) 전송 자체를 막는다. `handleSend`는 이미 `disabled`일 때 return하므로 추가 분기 불필요.
- placeholder 문구에 `offline` 케이스 추가: "지금은 여기서 대화할 수 없어요" (우선순위: 비로그인 > 스트리밍 중 > offline > 기본).

### 3. `frontend/src/pages/HomePage.tsx`

- JSX 구조·레이아웃은 변경하지 않는다.
- `<CuratorInput maxWidthClassName="max-w-xl" />` 호출에 `offline` prop만 추가: `<CuratorInput offline maxWidthClassName="max-w-xl" />`.
- `ChatMessages`는 그대로 둔다 (같은 세션이므로 `/me`에서 나눈 대화가 있으면 Home에서도 읽기용으로는 보임 — 전송만 막힘).

### 4. `frontend/src/components/shell/Sidebar.tsx`

- "채팅 기록"(`SectionLabel` + `chats.map(...)` 블록)을 제거한다.
- 관련 로컬 상태/핸들러(`editingId`, `editValue`, `startEdit`, `commitEdit`, `handleDeleteChat`, `handleChatClick`, `renameChat`, `deleteChat`, `clearChats`, `cachedSessions`, `setSession` 등 채팅 기록 전용 로직)도 함께 제거한다. 단, `clearMessages`(브랜드 클릭 시 초기화용)는 유지.
- 대신 `useSidebarStore`의 `analyses`/`loadAnalyses`(= `MyAnalysesPage`가 쓰는 것과 동일 소스)를 사용해 완료된 분석 목록을 표시한다: 제목 + 날짜, 클릭 시 `ROUTES.analysisDetail(item.id)`로 이동.
- 진행 중(job) 항목은 사이드바에서는 제외하고 완료된 스냅샷만 보여준다 (사이드바는 좁은 공간이라 진행 중 표시는 `/me` 허브에서만).
- 축소(collapsed, `expanded=false`) 상태의 아이콘 행은 `MessageSquare` 아이콘 대신 분석 목록을 상징하는 아이콘(예: 기존 임포트된 것 중 적절한 것, 없으면 `CircleDot` 등 추가)으로 교체.

## 에러 처리 / 엣지 케이스

- 분석 목록이 비어있으면 기존 "채팅 기록이 없습니다" 자리에 "아직 분석 결과가 없습니다" 류의 안내 문구를 넣는다.
- `AnalysisDetailPage`에서 비로그인 상태면 `CuratorInput`이 이미 처리하는 기존 로직(placeholder: "로그인 후 큐레이터와 대화할 수 있습니다") 그대로 적용된다.

## 테스트/검증

- `frontend`에서 `pnpm build`(타입체크 겸)로 통과 확인.
- 브라우저로 직접 확인: `/me/analyses/:id`에서 실제 질문 → 스트리밍 응답 수신, Home(`/`)에서는 입력해도 전송되지 않음(비활성 상태), 사이드바에 분석 목록이 뜨고 클릭 시 상세 이동.
