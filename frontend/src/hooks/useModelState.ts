import { useEffect, useState } from "react";

import {
  type LMStudioHealth,
  fetchLMStudioHealth,
  fetchLMStudioModels,
} from "../api/assistant";
import { type AppNotice, errorNotice } from "../utils/notices";

export function useModelState() {
  const [lmHealth, setLmHealth] = useState<LMStudioHealth | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelNotice, setModelNotice] = useState<AppNotice | null>(null);

  const selectedModelLoaded = lmHealth?.configured_chat_model_loaded === true;

  useEffect(() => {
    void refreshModelState();
  }, []);

  useEffect(() => {
    if (modelNotice?.type !== "success") {
      return;
    }
    const timeoutId = window.setTimeout(() => setModelNotice(null), 4000);
    return () => window.clearTimeout(timeoutId);
  }, [modelNotice]);

  async function refreshModelState({ clearNotice = true }: { clearNotice?: boolean } = {}) {
    if (clearNotice) {
      setModelNotice(null);
    }
    try {
      const [health, models] = await Promise.all([fetchLMStudioHealth(), fetchLMStudioModels()]);
      setLmHealth(health);
      setSelectedModel(health.configured_chat_model || models.configured_chat_model || "");
    } catch (exc) {
      setLmHealth(null);
      setModelNotice(errorNotice(exc));
    }
  }

  return {
    lmHealth,
    selectedModel,
    selectedModelLoaded,
    modelNotice,
    refreshModelState,
  };
}
