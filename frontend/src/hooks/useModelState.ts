import { useEffect, useState } from "react";

import {
  type LMStudioHealth,
  fetchLMStudioHealth,
  fetchLMStudioModels,
} from "../api/assistant";

export function useModelState() {
  const [lmHealth, setLmHealth] = useState<LMStudioHealth | null>(null);
  const [selectedModel, setSelectedModel] = useState("");

  const selectedModelLoaded = lmHealth?.configured_chat_model_loaded === true;

  useEffect(() => {
    void refreshModelState();
  }, []);

  async function refreshModelState() {
    try {
      const [health, models] = await Promise.all([fetchLMStudioHealth(), fetchLMStudioModels()]);
      setLmHealth(health);
      setSelectedModel(health.configured_chat_model || models.configured_chat_model || "");
    } catch {
      setLmHealth(null);
    }
  }

  return {
    lmHealth,
    selectedModel,
    selectedModelLoaded,
    refreshModelState,
  };
}
