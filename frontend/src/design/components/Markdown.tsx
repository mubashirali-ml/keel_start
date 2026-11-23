import ReactMarkdown from "react-markdown";

import { cn } from "@/lib/cn";

/** Light markdown for chat and documents; links open in a new tab; raw HTML is not rendered. */
export function Markdown({ children, className, size = "base" }: { children: string; className?: string; size?: "sm" | "base" }) {
  return (
    <div className={cn("prose max-w-none dark:prose-invert prose-a:font-medium", size === "sm" && "prose-sm", className)}>
      <ReactMarkdown
        skipHtml
        components={{
          a: ({ node: _node, children: linkText, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer">
              {linkText}
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
