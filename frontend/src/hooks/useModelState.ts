import { useEffect, useState } from "react";

import {
  type LMStudioHealth,
  fetchLMStudioHealth,
  fetchLMStudioModels,
  loadLMStudioChatModel,
  selectLMStudioChatModel,
  unloadLMStudioChatModel,
} from "../api/assistant";
import { type AppNotice, errorNotice, successNotice } from "../utils/notices";

export function useModelState() {
  const [lmHealth, setLmHealth] = useState<LMStudioHealth | null>(null);
  const [lmModels, setLmModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [isModelBusy, setIsModelBusy] = useState(false);
  const [modelNotice, setModelNotice] = useState<AppNotice | null>(null);

  const selectedModelLoaded = lmHealth?.selected_chat_model_loaded === true;
  const selectedModelAvailable = lmHealth?.selected_chat_model_available !== false;

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
      setLmModels(models.models);
      setSelectedModel(health.selected_chat_model || models.selected_chat_model || models.configured_chat_model || models.models[0] || "");
    } catch (exc) {
      setLmHealth(null);
      setModelNotice(errorNotice(exc));
    }
  }

  async function handleSelectModel(modelId: string) {
    setSelectedModel(modelId);
    setIsModelBusy(true);
    setModelNotice(null);
    try {
      await selectLMStudioChatModel(modelId);
      await refreshModelState({ clearNotice: false });
      setModelNotice(successNotice("Kiválasztva: " + modelId));
    } catch (exc) {
      setModelNotice(errorNotice(exc));
    } finally {
      setIsModelBusy(false);
    }
  }

  async function handleLoadModel() {
    if (selectedModel === "") {
      return;
    }
    setIsModelBusy(true);
    setModelNotice(null);
    try {
      const result = await loadLMStudioChatModel(selectedModel);
      await refreshModelState({ clearNotice: false });
      setModelNotice(successNotice("Betöltve: " + result.instance_id));
    } catch (exc) {
      setModelNotice(errorNotice(exc));
    } finally {
      setIsModelBusy(false);
    }
  }

  async function handleUnloadModel() {
    if (selectedModel === "") {
      return;
    }
    setIsModelBusy(true);
    setModelNotice(null);
    try {
      const result = await unloadLMStudioChatModel(selectedModel);
      await refreshModelState({ clearNotice: false });
      setModelNotice(successNotice("Leválasztva: " + result.instance_id));
    } catch (exc) {
      setModelNotice(errorNotice(exc));
    } finally {
      setIsModelBusy(false);
    }
  }

  return {
    lmHealth,
    lmModels,
    selectedModel,
    selectedModelAvailable,
    selectedModelLoaded,
    isModelBusy,
    modelNotice,
    refreshModelState,
    handleSelectModel,
    handleLoadModel,
    handleUnloadModel,
  };
}
