import { Moon, Sun } from "lucide-react";

import { type LMStudioHealth } from "../api/assistant";
import { normalizeErrorMessage } from "../utils/notices";

type ModelPanelProps = {
  chatTitle: string;
  health: LMStudioHealth | null;
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
};

export function ModelPanel({
  chatTitle,
  health,
  theme,
  onThemeChange,
}: ModelPanelProps) {
  const configuredMissing = health?.configured_chat_model_available === false;
  const PanelThemeIcon = theme === "light" ? Moon : Sun;
  const nextPanelTheme = theme === "light" ? "dark" : "light";

  return (
    <section className="model-panel" aria-label="Chat fejléc">
      <h1 className="model-chat-title">{chatTitle}</h1>

      <button className="icon-button" type="button" aria-label="Téma váltása" onClick={() => onThemeChange(nextPanelTheme)}>
        <PanelThemeIcon size={18} aria-hidden="true" />
      </button>

      {configuredMissing ? <p className="model-warning">A .env-ben beállított modell nem található az LM Studio listában: {health?.configured_chat_model}</p> : null}
      {health?.error_message ? <p className="model-warning">{normalizeErrorMessage(health.error_message)}</p> : null}
    </section>
  );
}
