import { useState } from "react";
import { ChevronDown, ListChecks } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type SavedWorkNarrationPanelProps = {
  content: string;
};

export function SavedWorkNarrationPanel({ content }: SavedWorkNarrationPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const displayContent = normalizeWorkNarrationMarkdown(content);
  if (displayContent === "") {
    return null;
  }

  return (
    <section className={"reasoning-panel saved-work-narration-panel " + (isOpen ? "is-open" : "is-preview")} aria-label="Mentett munkalépések">
      <button className="reasoning-panel__header" type="button" onClick={() => setIsOpen((value) => !value)} aria-expanded={isOpen}>
        <span className="reasoning-panel__status">
          <span className="saved-work-narration-panel__icon" aria-hidden="true">
            <ListChecks size={15} />
          </span>
          Munkalépések
        </span>
        <span className="reasoning-panel__toggle">
          {isOpen ? "Bezárás" : "Megnyitás"}
          <ChevronDown size={15} aria-hidden="true" />
        </span>
      </button>
      {isOpen ? (
        <div className="reasoning-panel__body">
          <div className="reasoning-panel__content saved-work-narration-panel__content"><ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown></div>
        </div>
      ) : null}
    </section>
  );
}

function normalizeWorkNarrationMarkdown(value: string) {
  const compact = value
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/\n{2,}/g, "\n")
    .replace(/^\n+/, "")
    .trim();

  if (compact.split("\n").filter(Boolean).length > 1) {
    return compact;
  }

  return compact.replace(/([.!?])\s+(?=[A-ZÁÉÍÓÖŐÚÜŰ])/g, "\n");
}
