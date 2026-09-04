"use client";

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { normalizeEvidenceMarkdown } from "@/lib/markdown";

type MarkdownExcerptProps = {
  markdown: string;
};

function ExcerptHeading({ children }: { children?: ReactNode }) {
  return <h3 className="evidence-excerpt__heading">{children}</h3>;
}

export function MarkdownExcerpt({ markdown }: MarkdownExcerptProps) {
  return (
    <div className="evidence-excerpt">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ExcerptHeading,
          h2: ExcerptHeading,
          h3: ExcerptHeading,
          h4: ExcerptHeading,
        }}
      >
        {normalizeEvidenceMarkdown(markdown)}
      </ReactMarkdown>
    </div>
  );
}
