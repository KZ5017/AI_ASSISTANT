import { BookOpen, Database, Lightbulb, LightbulbOff, Network } from "lucide-react";
import { type AssistantToolMode } from "../api/assistant";

type ComposerModeBarProps = {
  reasoningEnabled: boolean;
  activeToolMode: AssistantToolMode;
  disabled: boolean;
  onReasoningToggle: () => void;
  onToolModeToggle: (toolMode: AssistantToolMode) => void;
};

export function ComposerModeBar({
  reasoningEnabled,
  activeToolMode,
  disabled,
  onReasoningToggle,
  onToolModeToggle,
}: ComposerModeBarProps) {
  const obsidianActive = activeToolMode === "obsidian";
  const excelActive = activeToolMode === "excel";
  const graphragActive = activeToolMode === "graphrag";

  return (
    <div className="composer-mode-bar" aria-label="Chat módok">
      <button className={"mode-toggle reasoning-toggle " + (reasoningEnabled ? "is-active" : "")} type="button" aria-pressed={reasoningEnabled} disabled={disabled} onClick={onReasoningToggle} title={reasoningEnabled ? "Gondolkodó mód bekapcsolva" : "Gondolkodó mód kikapcsolva"}>
        {reasoningEnabled ? <Lightbulb size={17} aria-hidden="true" /> : <LightbulbOff size={17} aria-hidden="true" />}
        Gondolkodó
      </button>
      <button className={"mode-toggle tool-mode-toggle " + (obsidianActive ? "is-active" : "")} type="button" aria-pressed={obsidianActive} disabled={disabled} onClick={() => onToolModeToggle("obsidian")} title={obsidianActive ? "Rögzített tudásanyagból történő válaszadás mód bekapcsolva." : "Rögzített tudásanyagból történő válaszadás mód kikapcsolva."}>
        <BookOpen size={17} aria-hidden="true" />
        Tudásbázis
      </button>
      <button className={"mode-toggle tool-mode-toggle " + (excelActive ? "is-active" : "")} type="button" aria-pressed={excelActive} disabled={disabled} onClick={() => onToolModeToggle("excel")} title={excelActive ? "Adatbázisból történő válaszadás mód bekapcsolva." : "Adatbázisból történő válaszadás mód kikapcsolva."}>
        <Database size={17} aria-hidden="true" />
        Adatbázis
      </button>
      <button className={"mode-toggle tool-mode-toggle " + (graphragActive ? "is-active" : "")} type="button" aria-pressed={graphragActive} disabled={disabled} onClick={() => onToolModeToggle("graphrag")} title={graphragActive ? "GraphRAG alapú válaszadás bekapcsolva." : "GraphRAG alapú válaszadás kikapcsolva."}>
        <Network size={17} aria-hidden="true" />
        GraphRAG
      </button>
    </div>
  );
}
