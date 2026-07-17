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
  const contentRef = useRef<HTMLDivElement | null>(null);
  const autoScrollEnabledRef = useRef(true);
  const pendingFrameRef = useRef<number | null>(null);
  const displayContent = normalizeReasoningMarkdown(content);

  useEffect(() => {
    followBottomIfEnabled();
  }, [displayContent, isOpen]);

  useEffect(() => {
    const bodyElement = bodyRef.current;
    if (!bodyElement) {
      return;
    }

    const observer = new ResizeObserver(() => {
      followBottomIfEnabled();
    });
    observer.observe(bodyElement);
    if (contentRef.current) {
      observer.observe(contentRef.current);
    }

    return () => {
      observer.disconnect();
      if (pendingFrameRef.current !== null) {
        window.cancelAnimationFrame(pendingFrameRef.current);
      }
    };
  }, []);

  function handleScroll() {
    const element = bodyRef.current;
    if (!element) {
      return;
    }
    autoScrollEnabledRef.current = isNearScrollBottom(element);
  }

  function followBottomIfEnabled() {
    if (!autoScrollEnabledRef.current) {
      return;
    }
    if (pendingFrameRef.current !== null) {
      window.cancelAnimationFrame(pendingFrameRef.current);
    }
    pendingFrameRef.current = window.requestAnimationFrame(() => {
      pendingFrameRef.current = null;
      const element = bodyRef.current;
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    });
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
        <div className="reasoning-panel__content" ref={contentRef}><ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown></div>
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
