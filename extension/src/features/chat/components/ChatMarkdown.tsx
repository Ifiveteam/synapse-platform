import ReactMarkdown from 'react-markdown'

interface ChatMarkdownProps {
  content: string
}

/** assistant 답변 마크다운 렌더 — 사이드패널 text-xs 스케일에 맞춘 타이포 */
export function ChatMarkdown({ content }: ChatMarkdownProps) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-4">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-4">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
          >
            {children}
          </a>
        ),
        code: ({ children }) => (
          <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] text-slate-800">
            {children}
          </code>
        ),
        h1: ({ children }) => <p className="mb-2 font-semibold text-slate-900">{children}</p>,
        h2: ({ children }) => <p className="mb-2 font-semibold text-slate-900">{children}</p>,
        h3: ({ children }) => <p className="mb-1.5 font-semibold text-slate-900">{children}</p>,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
