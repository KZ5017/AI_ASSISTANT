import { useState } from "react";
import { ChevronDown, FileSearch } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type SavedToolActivityPanelProps = {
  content: string;
};

export function SavedToolActivityPanel({ content }: SavedToolActivityPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const displayContent = normalizeToolActivityMarkdown(content);

  if (displayContent === "") {
    return null;
  }

  return (
    <section className={"reasoning-panel tool-activity-panel saved-tool-activity-panel " + (isOpen ? "is-open" : "is-preview")} aria-label="Mentett eszközhasználat">
      <button className="reasoning-panel__header" type="button" onClick={() => setIsOpen((value) => !value)} aria-expanded={isOpen}>
        <span className="reasoning-panel__status">
          <span className="tool-activity-panel__icon" aria-hidden="true">
            <FileSearch size={15} />
          </span>
          Eszközhasználat
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

function normalizeToolActivityMarkdown(value: string) {
  return value
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^\n+/, "")
    .trimEnd();
}
