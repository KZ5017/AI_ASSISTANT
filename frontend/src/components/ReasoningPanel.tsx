import { useEffect, useRef } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ReasoningPanelProps = {
  content: string;
  isOpen: boolean;
  onToggle: () => void;
};

export function ReasoningPanel({ content, isOpen, onToggle }: ReasoningPanelProps) {
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const autoScrollEnabledRef = useRef(true);
  const displayContent = normalizeReasoningMarkdown(content);

  useEffect(() => {
    const element = bodyRef.current;
    if (element && autoScrollEnabledRef.current) {
      element.scrollTop = element.scrollHeight;
    }
  }, [displayContent, isOpen]);

  function handleScroll() {
    const element = bodyRef.current;
    if (!element) {
      return;
    }
    autoScrollEnabledRef.current = isNearScrollBottom(element);
  }

  if (content === "") {
    return null;
  }

  return (
    <section className={"reasoning-panel " + (isOpen ? "is-open" : "is-preview")} aria-label="Gondolatmenet">
      <button className="reasoning-panel__header" type="button" onClick={onToggle} aria-expanded={isOpen}>
        <span className="reasoning-panel__status">
          <span className="reasoning-panel__pulse" aria-hidden="true">
            <Lightbulb size={15} />
          </span>
          Gondolkodik
        </span>
        <span className="reasoning-panel__toggle">
          Gondolatmenet
          <ChevronDown size={15} aria-hidden="true" />
        </span>
      </button>
      <div className="reasoning-panel__body" ref={bodyRef} onScroll={handleScroll}>
        <div className="reasoning-panel__content"><ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown></div>
      </div>
    </section>
  );
}

function normalizeReasoningMarkdown(value: string) {
  return value
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/\n{2,}/g, "\n")
    .replace(/^\n+/, "");
}

function isNearScrollBottom(element: HTMLElement) {
  return element.scrollHeight - element.scrollTop - element.clientHeight < 24;
}
