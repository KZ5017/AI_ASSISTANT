import { isValidElement, type ComponentPropsWithoutRef, type ReactNode, useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

type AssistantMarkdownProps = {
  children: string;
};

type CopyStatus = "idle" | "copied" | "error";

const assistantMarkdownComponents: Components = {
  pre: CodeBlock,
};

export function AssistantMarkdown({ children }: AssistantMarkdownProps) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={assistantMarkdownComponents}>
      {children}
    </ReactMarkdown>
  );
}

function CodeBlock({ children }: ComponentPropsWithoutRef<"pre">) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const resetTimerRef = useRef<number | null>(null);
  const codeText = extractText(children).replace(/\n$/, "");

  useEffect(() => {
    return () => {
      if (resetTimerRef.current !== null) {
        window.clearTimeout(resetTimerRef.current);
      }
    };
  }, []);

  async function handleCopy() {
    if (resetTimerRef.current !== null) {
      window.clearTimeout(resetTimerRef.current);
    }

    try {
      await navigator.clipboard.writeText(codeText);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("error");
    }

    resetTimerRef.current = window.setTimeout(() => {
      setCopyStatus("idle");
      resetTimerRef.current = null;
    }, 1400);
  }

  const copyLabel =
    copyStatus === "copied"
      ? "Kód kimásolva"
      : copyStatus === "error"
        ? "A kód másolása sikertelen"
        : "Kód másolása";

  return (
    <div className="code-block">
      <div className="code-block__toolbar">
        <button
          className={"code-block__copy-button" + (copyStatus === "copied" ? " is-copied" : "")}
          type="button"
          onClick={handleCopy}
          aria-label={copyLabel}
          title={copyLabel}
        >
          {copyStatus === "copied" ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  );
}

function extractText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(extractText).join("");
  }
  if (isValidElement<{ children?: ReactNode }>(node)) {
    return extractText(node.props.children);
  }
  return "";
}
