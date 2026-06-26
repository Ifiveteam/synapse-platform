/**
 * 페이지 추출 호출 옵션 타입.
 *
 * 역할: `extractVisiblePageText` / `extractPageTextSnapshot`에 전달하는 설정.
 * 하는 일: iframe DOM 직접 접근 전략 포함 여부 등 옵션을 정의한다.
 */
export interface ExtractPageTextOptions {
  /** false이면 same-origin iframe DOM 직접 접근 전략을 생략 (all_frames 통합용) */
  includeEmbeddedIframes?: boolean
}
