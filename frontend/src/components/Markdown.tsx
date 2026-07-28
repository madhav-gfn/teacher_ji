import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

interface MarkdownProps {
  children: string;
  className?: string;
}

// Shared renderer for any teaching/chat text that may contain math notation
// ($x^2$, $$\frac{1}{2}$$) or basic Markdown (lists, bold, tables) - the LLM
// prompts don't force plain text, so NCERT-style worked examples can come
// back with real notation instead of being flattened to ASCII.
export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children: paragraphChildren }) => (
            <p className="leading-7">{paragraphChildren}</p>
          ),
          ul: ({ children: listChildren }) => (
            <ul className="list-disc space-y-1 pl-5">{listChildren}</ul>
          ),
          ol: ({ children: listChildren }) => (
            <ol className="list-decimal space-y-1 pl-5">{listChildren}</ol>
          ),
          code: ({ children: codeChildren }) => (
            <code className="rounded bg-black/5 px-1.5 py-0.5 font-mono text-[0.9em]">
              {codeChildren}
            </code>
          ),
          a: ({ children: linkChildren, href }) => (
            <a href={href} className="underline decoration-dotted" target="_blank" rel="noreferrer">
              {linkChildren}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
