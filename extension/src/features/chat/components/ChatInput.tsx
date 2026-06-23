/**
 * AI 채팅 입력 콘솔 — ChatProvider가 공급하는 sendMessage·isGenerating과 연동한다.
 */
import { useState, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useChatContext } from '@/features/chat/context/ChatProvider'

export function ChatInput() {
  const [inputText, setInputText] = useState('')
  const { sendMessage, isGenerating } = useChatContext()

  const handleSubmit = () => {
    const trimmed = inputText.trim()
    if (!trimmed || isGenerating) return

    void sendMessage(trimmed)
    setInputText('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }

  const isSendable = inputText.trim().length > 0 && !isGenerating

  return (
    <div className="flex w-full items-center gap-2">
      <Input
        type="text"
        placeholder={
          isGenerating ? 'AI가 답변을 생성하는 중입니다...' : 'Synapse AI에게 질문하기...'
        }
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isGenerating}
        className="h-9 flex-1 border-slate-200 bg-slate-50 text-xs transition-all focus-visible:ring-slate-400 disabled:opacity-60"
        aria-label="AI 질문 입력창"
      />

      <Button
        type="button"
        onClick={handleSubmit}
        disabled={!isSendable}
        size="sm"
        className="h-9 shrink-0 px-3 text-xs font-semibold"
      >
        {isGenerating ? (
          <span className="flex items-center gap-1">
            <svg className="h-3 w-3 animate-spin text-slate-400" viewBox="0 0 24 24" aria-hidden>
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            생성 중
          </span>
        ) : (
          '전송'
        )}
      </Button>
    </div>
  )
}
