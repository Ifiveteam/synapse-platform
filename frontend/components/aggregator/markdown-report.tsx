"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

interface MarkdownReportProps {
  content: string;
  className?: string;
}

export function MarkdownReport({ content, className }: MarkdownReportProps) {
  return (
    <article
      className={cn(
        "text-foreground space-y-4 text-sm leading-relaxed sm:text-base",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mt-2 text-2xl font-bold tracking-tight">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-8 border-b pb-2 text-xl font-semibold">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-6 text-lg font-semibold">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="text-muted-foreground leading-7">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="text-muted-foreground list-disc space-y-1 pl-5">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="text-muted-foreground list-decimal space-y-1 pl-5">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-7">{children}</li>,
          strong: ({ children }) => (
            <strong className="text-foreground font-semibold">{children}</strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-primary/30 text-muted-foreground border-l-4 pl-4 italic">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[480px] text-left text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/60 text-foreground">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="border-b px-3 py-2 font-semibold">{children}</th>
          ),
          td: ({ children }) => (
            <td className="border-b px-3 py-2 align-top">{children}</td>
          ),
          code: ({ children }) => (
            <code className="bg-muted rounded px-1.5 py-0.5 font-mono text-xs">
              {children}
            </code>
          ),
          hr: () => <hr className="border-border my-6" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
