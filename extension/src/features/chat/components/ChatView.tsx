/**
 * AI 채팅 타임라인 — 활성 탭 맥락 배너와 SSE 스트리밍 대화 UI.
 */
import { Card, CardContent } from '@/components/ui/card'
import { ChatMarkdown } from '@/features/chat/components/ChatMarkdown'
import { StreamStatusIndicator } from '@/features/chat/components/StreamStatusIndicator'
import { useChatContext } from '@/features/chat/context/ChatProvider'

function resolveHostname(url: string) {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export function ChatView() {
  const { messages, currentContext, currentStatus, isGenerating, scrollAnchorRef } =
    useChatContext()

  const lastAssistantIndex = messages.reduce(
    (found, msg, index) => (msg.role === 'assistant' ? index : found),
    -1,
  )

  return (
    <div className="flex min-h-full flex-col gap-4">
      {currentContext ? (
        <Card className="shrink-0 border-emerald-100 bg-emerald-50/40 shadow-none">
          <CardContent className="flex items-start gap-2.5 p-3 text-xs">
            <span className="mt-0.5 text-base leading-none">💡</span>
            <div className="flex-1 overflow-hidden">
              <p className="truncate font-semibold text-emerald-900" title={currentContext.title}>
                {currentContext.title}
              </p>
              <p className="mt-0.5 truncate text-[10px] text-emerald-600/80">
                {resolveHostname(currentContext.url)} 도메인 분석 중
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="shrink-0 border-slate-100 bg-slate-50/50 shadow-none">
          <CardContent className="p-3 text-center text-xs text-slate-400">
            🌐 현재 페이지는 시스템·민감 도메인이므로 맥락 추적에서 제외됩니다.
          </CardContent>
        </Card>
      )}

      <div className="flex flex-1 flex-col gap-3.5">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-slate-400/80">
            <div className="mb-3 text-3xl">🧠</div>
            <p className="text-xs font-semibold text-slate-600">Synapse 인텔리전스 결합 완료</p>
            <p className="mt-1 max-w-[200px] text-[10px] leading-relaxed text-slate-400">
              방금 보신 블로그 코스나 맛집 정보에 대해 궁금한 점을 질문해 보세요!
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            if (msg.role === 'system') {
              return (
                <div key={msg.id} className="flex w-full justify-center px-2">
                  <p className="max-w-[90%] rounded-full bg-slate-100 px-3 py-1.5 text-center text-[10px] leading-relaxed text-slate-600">
                    {msg.content}
                  </p>
                </div>
              )
            }

            const isLastAssistantStreaming =
              isGenerating && index === messages.length - 1 && msg.role === 'assistant'
            const isLastAssistant = index === lastAssistantIndex && msg.role === 'assistant'

            return (
              <div
                key={msg.id}
                className={`flex max-w-[85%] flex-col gap-1 ${
                  msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'
                }`}
              >
                {msg.role === 'assistant' && isLastAssistantStreaming && currentStatus && (
                  <StreamStatusIndicator status={currentStatus} />
                )}

                {(msg.role === 'user' || msg.content.length > 0) && (
                  <div
                    className={`rounded-2xl px-3.5 py-2 text-xs leading-relaxed ${
                      msg.role === 'user'
                        ? 'rounded-tr-sm bg-slate-900 text-white whitespace-pre-wrap'
                        : 'rounded-tl-sm border border-slate-100 bg-white text-slate-800 shadow-sm'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <ChatMarkdown content={msg.content} />
                    ) : (
                      msg.content
                    )}
                  </div>
                )}

                {isLastAssistant && msg.content.length > 0 && !isGenerating ? (
                  <span className="px-1 text-[9px] text-slate-400">
                    이 답변을 스크랩하려면 하단 📌 버튼을 누르세요
                  </span>
                ) : null}

                <span className="px-1 text-[10px] text-slate-400">{msg.timestamp}</span>
              </div>
            )
          })
        )}

        <div ref={scrollAnchorRef} />
      </div>
    </div>
  )
}
