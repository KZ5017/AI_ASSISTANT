import { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type SavedReasoningPanelProps = {
  content: string;
};

export function SavedReasoningPanel({ content }: SavedReasoningPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const displayContent = normalizeReasoningMarkdown(content);

  if (displayContent === "") {
    return null;
  }

  return (
    <section className={"reasoning-panel saved-reasoning-panel " + (isOpen ? "is-open" : "is-preview")} aria-label="Mentett gondolatmenet">
      <button className="reasoning-panel__header" type="button" onClick={() => setIsOpen((value) => !value)} aria-expanded={isOpen}>
        <span className="reasoning-panel__status">
          <span className="saved-reasoning-panel__icon" aria-hidden="true">
            <Lightbulb size={15} />
          </span>
          Gondolatmenet
        </span>
        <span className="reasoning-panel__toggle">
          {isOpen ? "Bezárás" : "Megnyitás"}
          <ChevronDown size={15} aria-hidden="true" />
        </span>
      </button>
      {isOpen ? (
        <div className="reasoning-panel__body">
          <div className="reasoning-panel__content"><ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown></div>
        </div>
      ) : null}
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
