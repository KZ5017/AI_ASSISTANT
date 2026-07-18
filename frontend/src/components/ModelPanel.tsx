import { Moon, Sun } from "lucide-react";

import { type LMStudioHealth } from "../api/assistant";
import { type AppNotice, normalizeErrorMessage } from "../utils/notices";

type ModelPanelProps = {
  chatTitle: string;
  health: LMStudioHealth | null;
  selectedModel: string;
  selectedModelLoaded: boolean;
  notice: AppNotice | null;
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
  onRefresh: () => void;
};

export function ModelPanel({
  chatTitle,
  health,
  selectedModel,
  selectedModelLoaded,
  notice,
  theme,
  onThemeChange,
  onRefresh,
}: ModelPanelProps) {
  const statusText = !health
    ? "Ismeretlen"
    : !health.reachable
      ? "Nem elérhető"
      : selectedModelLoaded
        ? "Betöltve"
        : "Nincs betöltve";
  const configuredMissing = health?.configured_chat_model_available === false;
  const PanelThemeIcon = theme === "light" ? Moon : Sun;
  const nextPanelTheme = theme === "light" ? "dark" : "light";

  return (
    <section className="model-panel" aria-label="Chat és modell állapot">
      <div className="model-summary">
        <div className="model-status-line">
          <span className="model-status-label">Modell állapot:</span>
          <span className={"status-dot " + (selectedModelLoaded ? "is-ok" : "is-warning")} />
          <strong>{statusText}</strong>
        </div>
        <p className={"model-notice " + (notice ? "is-" + notice.type : "is-hidden")} aria-live="polite" aria-hidden={notice ? undefined : true}>{notice?.message ?? "Értesítés helye"}</p>
        <h1 className="model-chat-title">{chatTitle}</h1>
      </div>

      <div className="model-controls">
        <div className="model-current" title={selectedModel || undefined}>{selectedModel || "Nincs beállított modell"}</div>
        <div className="model-actions">
          <button className="secondary-action" type="button" onClick={onRefresh}>Frissítés</button>
          <button className="icon-button" type="button" aria-label="Téma váltása" onClick={() => onThemeChange(nextPanelTheme)}>
            <PanelThemeIcon size={18} aria-hidden="true" />
          </button>
        </div>
      </div>

      {configuredMissing ? <p className="model-warning">A .env-ben beállított modell nem található az LM Studio listában: {health?.configured_chat_model}</p> : null}
      {health?.error_message ? <p className="model-warning">{normalizeErrorMessage(health.error_message)}</p> : null}
    </section>
  );
}
