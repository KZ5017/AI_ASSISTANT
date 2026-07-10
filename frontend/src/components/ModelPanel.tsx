import { Moon, Sun } from "lucide-react";

import { type LMStudioHealth } from "../api/assistant";
import { type AppNotice, normalizeErrorMessage } from "../utils/notices";

type ModelPanelProps = {
  chatTitle: string;
  health: LMStudioHealth | null;
  models: string[];
  selectedModel: string;
  selectedModelAvailable: boolean;
  selectedModelLoaded: boolean;
  isBusy: boolean;
  notice: AppNotice | null;
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
  onRefresh: () => void;
  onSelect: (modelId: string) => void;
  onLoad: () => void;
  onUnload: () => void;
};

export function ModelPanel({
  chatTitle,
  health,
  models,
  selectedModel,
  selectedModelAvailable,
  selectedModelLoaded,
  isBusy,
  notice,
  theme,
  onThemeChange,
  onRefresh,
  onSelect,
  onLoad,
  onUnload,
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
        <label className="model-select-label">
          <select value={selectedModel} disabled={isBusy || models.length === 0} onChange={(event) => onSelect(event.target.value)}>
            {models.length === 0 ? <option value="">Nincs modell</option> : null}
            {models.map((model) => (
              <option value={model} key={model}>{model}</option>
            ))}
          </select>
        </label>
        <div className="model-actions">
          <button className="secondary-action" type="button" onClick={onRefresh} disabled={isBusy}>Frissítés</button>
          <button className="secondary-action" type="button" onClick={onLoad} disabled={isBusy || selectedModel === "" || !selectedModelAvailable || selectedModelLoaded}>Betöltés</button>
          <button className="secondary-action" type="button" onClick={onUnload} disabled={isBusy || selectedModel === "" || !selectedModelLoaded}>Leválasztás</button>
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
