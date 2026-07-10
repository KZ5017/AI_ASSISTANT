export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export type AssistantStatus = {
  status: string;
  context_char_budget: number;
};

export type AssistantReasoningMode = 'normal' | 'model_default';
export type AssistantMessageRole = 'user' | 'assistant' | 'system';

export type AssistantMessage = {
  id: number;
  role: AssistantMessageRole;
  content: string;
  sequence_index: number;
  model: string | null;
  reasoning_mode: string | null;
  created_at: string;
};

export type AssistantChatSummary = {
  id: number;
  title: string;
  status: string;
  reasoning_mode: string;
  temperature: number | null;
  created_at: string;
  updated_at: string;
};

export type AssistantChatDetail = AssistantChatSummary & {
  messages: AssistantMessage[];
};

export type AssistantChatList = {
  chats: AssistantChatSummary[];
};

export type ContextLimitDetail = {
  code: 'context_limit_exceeded';
  message: string;
  budget: number;
  actual: number;
};

export type LMStudioHealth = {
  provider: string;
  base_url: string;
  reachable: boolean;
  model_ids: string[];
  configured_chat_model: string;
  selected_chat_model: string;
  configured_chat_model_available: boolean | null;
  configured_chat_model_loaded: boolean | null;
  selected_chat_model_available: boolean | null;
  selected_chat_model_loaded: boolean | null;
  loaded_model_ids: string[];
  error_message: string | null;
};

export type LMStudioModels = {
  models: string[];
  loaded_model_ids: string[];
  configured_chat_model: string;
  selected_chat_model: string;
};

export type LMStudioLoadResult = {
  type: string;
  instance_id: string;
  load_time_seconds: number | null;
  status: string;
  load_config: Record<string, unknown> | null;
  selected_chat_model: string;
};

export type LMStudioUnloadResult = {
  instance_id: string;
};

export type LMStudioSelectResult = {
  selected_chat_model: string;
  selected_chat_model_available: boolean | null;
  selected_chat_model_loaded: boolean | null;
  loaded_model_ids: string[];
};

export type LMStudioChatMessage = {
  role: 'system' | 'user' | 'assistant';
  content: string;
};

export type LMStudioChatRequest = {
  messages: LMStudioChatMessage[];
  model?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  reasoning_mode?: 'off' | 'model_default' | null;
};

export type LMStudioChatResponse = {
  model: string;
  content: string;
};

export async function fetchAssistantStatus(): Promise<AssistantStatus> {
  const response = await fetch(API_BASE_URL + '/assistant/status');
  return readJsonResponse<AssistantStatus>(response, 'Nem sikerült lekérdezni az asszisztens állapotát.');
}

export async function listAssistantChats(): Promise<AssistantChatList> {
  const response = await fetch(API_BASE_URL + '/assistant/chats');
  return readJsonResponse<AssistantChatList>(response, 'Nem sikerült betölteni a beszélgetéseket.');
}

export async function createAssistantChat(payload: { reasoning_mode?: AssistantReasoningMode } = {}): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült új beszélgetést létrehozni.');
}

export async function getAssistantChat(chatId: number): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId);
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült betölteni a beszélgetést.');
}

export async function renameAssistantChat(chatId: number, title: string): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült átnevezni a beszélgetést.');
}

export async function deleteAssistantChat(chatId: number): Promise<{ status: string }> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId, { method: 'DELETE' });
  return readJsonResponse<{ status: string }>(response, 'Nem sikerült törölni a beszélgetést.');
}

export async function sendAssistantMessage(
  chatId: number,
  payload: { content: string; reasoning_mode?: AssistantReasoningMode | null },
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült elküldeni az üzenetet.');
}

export async function regenerateAssistantMessage(
  chatId: number,
  payload: { reasoning_mode?: AssistantReasoningMode | null },
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/regenerate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült újragenerálni a választ.');
}

export async function fetchLMStudioHealth(): Promise<LMStudioHealth> {
  const response = await fetch(API_BASE_URL + '/lm-studio/health');
  return readJsonResponse<LMStudioHealth>(response, 'Nem sikerült lekérdezni az LM Studio állapotát.');
}

export async function fetchLMStudioModels(): Promise<LMStudioModels> {
  const response = await fetch(API_BASE_URL + '/lm-studio/models');
  return readJsonResponse<LMStudioModels>(response, 'Nem sikerült lekérdezni az LM Studio modelleket.');
}

export async function selectLMStudioChatModel(modelId: string): Promise<LMStudioSelectResult> {
  const response = await fetch(API_BASE_URL + '/lm-studio/select-chat-model', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  });
  return readJsonResponse<LMStudioSelectResult>(response, 'Nem sikerült kiválasztani a chat modellt.');
}

export async function loadLMStudioChatModel(modelId?: string | null): Promise<LMStudioLoadResult> {
  const response = await fetch(API_BASE_URL + '/lm-studio/load-chat-model', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId ?? null }),
  });
  return readJsonResponse<LMStudioLoadResult>(response, 'Nem sikerült betölteni a chat modellt.');
}

export async function unloadLMStudioChatModel(modelId?: string | null): Promise<LMStudioUnloadResult> {
  const response = await fetch(API_BASE_URL + '/lm-studio/unload-chat-model', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId ?? null }),
  });
  return readJsonResponse<LMStudioUnloadResult>(response, 'Nem sikerült leválasztani a chat modellt.');
}

export async function sendLMStudioChat(payload: LMStudioChatRequest): Promise<LMStudioChatResponse> {
  const response = await fetch(API_BASE_URL + '/lm-studio/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<LMStudioChatResponse>(response, 'Nem sikerült választ kérni az LM Studio-tól.');
}

async function readJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    let detail = fallbackMessage;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === 'string') {
        detail = payload.detail;
      } else if (isContextLimitDetail(payload.detail)) {
        detail = payload.detail.message;
      }
    } catch {
      // Keep fallback when the backend did not return JSON.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

function isContextLimitDetail(value: unknown): value is ContextLimitDetail {
  return typeof value === 'object' && value !== null && 'code' in value && 'message' in value;
}
