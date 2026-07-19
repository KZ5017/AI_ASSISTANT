export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export type AssistantStatus = {
  status: string;
  context_char_budget: number;
};

export type AssistantReasoningMode = 'normal' | 'model_default';
export type AssistantToolMode = 'none' | 'obsidian' | 'excel';
export type AssistantMessageRole = 'user' | 'assistant' | 'system';

export type AssistantMessage = {
  id: number;
  role: AssistantMessageRole;
  content: string;
  reasoning_content: string | null;
  tool_activity_content: string | null;
  work_narration_content: string | null;
  generation_duration_ms: number | null;
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


export type AssistantStreamEvent =
  | { event: 'start'; data: { chat_id: number } }
  | { event: 'delta'; data: { content: string } }
  | { event: 'reasoning_delta'; data: { content: string } }
  | { event: 'tool_activity'; data: { content: string; raw: unknown } }
  | { event: 'status'; data: { raw: unknown } }
  | { event: 'error'; data: { message: string } }
  | { event: 'done'; data: { chat: AssistantChatDetail } };

export type AssistantStreamHandlers = {
  onStart?: (data: { chat_id: number }) => void;
  onDelta?: (content: string) => void;
  onReasoningDelta?: (content: string) => void;
  onToolActivity?: (content: string, raw: unknown) => void;
  onStatus?: (raw: unknown) => void;
  onError?: (message: string) => void;
};

export type AssistantStreamOptions = {
  handlers?: AssistantStreamHandlers;
  signal?: AbortSignal;
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
  payload: { content: string; reasoning_mode?: AssistantReasoningMode | null; tool_mode?: AssistantToolMode },
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült elküldeni az üzenetet.');
}


export async function updateAssistantMessage(
  chatId: number,
  messageId: number,
  payload: { content: string },
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + "/assistant/chats/" + chatId + "/messages/" + messageId, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<AssistantChatDetail>(response, "Nem sikerült menteni az üzenetet.");
}


export async function streamAssistantMessage(
  chatId: number,
  payload: { content: string; reasoning_mode?: AssistantReasoningMode | null; tool_mode?: AssistantToolMode },
  options: AssistantStreamOptions = {},
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/messages/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: options.signal,
  });

  return readAssistantChatStream(response, 'Nem sikerült elküldeni az üzenetet.', options.handlers ?? {});
}

export async function streamRetryLastUserMessage(
  chatId: number,
  payload: { reasoning_mode?: AssistantReasoningMode | null; tool_mode?: AssistantToolMode },
  options: AssistantStreamOptions = {},
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/retry-last-user/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: options.signal,
  });

  return readAssistantChatStream(response, 'Nem sikerült újraküldeni az üzenetet.', options.handlers ?? {});
}

export async function regenerateAssistantMessage(
  chatId: number,
  payload: { reasoning_mode?: AssistantReasoningMode | null; tool_mode?: AssistantToolMode },
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/regenerate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return readJsonResponse<AssistantChatDetail>(response, 'Nem sikerült újragenerálni a választ.');
}

export async function streamRegenerateAssistantMessage(
  chatId: number,
  payload: { reasoning_mode?: AssistantReasoningMode | null; tool_mode?: AssistantToolMode },
  options: AssistantStreamOptions = {},
): Promise<AssistantChatDetail> {
  const response = await fetch(API_BASE_URL + '/assistant/chats/' + chatId + '/regenerate/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: options.signal,
  });

  return readAssistantChatStream(response, 'Nem sikerült újragenerálni a választ.', options.handlers ?? {});
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


async function readAssistantChatStream(
  response: Response,
  fallbackMessage: string,
  handlers: AssistantStreamHandlers,
): Promise<AssistantChatDetail> {
  if (!response.ok) {
    await readJsonResponse<never>(response, fallbackMessage);
  }

  if (!response.body) {
    throw new Error('A böngésző nem adott olvasható streaming választ.');
  }

  let doneChat: AssistantChatDetail | null = null;
  await readSseStream(response.body, (streamEvent) => {
    if (streamEvent.event === 'start') {
      handlers.onStart?.(streamEvent.data);
      return;
    }
    if (streamEvent.event === 'delta') {
      handlers.onDelta?.(streamEvent.data.content);
      return;
    }
    if (streamEvent.event === 'reasoning_delta') {
      handlers.onReasoningDelta?.(streamEvent.data.content);
      return;
    }
    if (streamEvent.event === 'tool_activity') {
      handlers.onToolActivity?.(streamEvent.data.content, streamEvent.data.raw);
      return;
    }
    if (streamEvent.event === 'status') {
      handlers.onStatus?.(streamEvent.data.raw);
      return;
    }
    if (streamEvent.event === 'error') {
      handlers.onError?.(streamEvent.data.message);
      throw new Error(streamEvent.data.message);
    }
    doneChat = streamEvent.data.chat;
  });

  if (!doneChat) {
    throw new Error('A streaming válasz lezárult végleges chat állapot nélkül.');
  }

  return doneChat;
}

async function readSseStream(body: ReadableStream<Uint8Array>, onEvent: (event: AssistantStreamEvent) => void): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    buffer = consumeSseBuffer(buffer, onEvent);
    if (done) {
      break;
    }
  }

  const trailing = buffer.trim();
  if (trailing !== '') {
    dispatchSseBlock(trailing, onEvent);
  }
}

function consumeSseBuffer(buffer: string, onEvent: (event: AssistantStreamEvent) => void): string {
  const normalized = buffer.replace(/\r\n/g, '\n');
  const blocks = normalized.split('\n\n');
  const remainder = blocks.pop() ?? '';
  for (const block of blocks) {
    dispatchSseBlock(block, onEvent);
  }
  return remainder;
}

function dispatchSseBlock(block: string, onEvent: (event: AssistantStreamEvent) => void): void {
  let eventName = 'message';
  const dataLines: string[] = [];

  for (const line of block.split('\n')) {
    if (line === '' || line.startsWith(':')) {
      continue;
    }
    const separatorIndex = line.indexOf(':');
    if (separatorIndex === -1) {
      continue;
    }
    const field = line.slice(0, separatorIndex);
    const value = line.slice(separatorIndex + 1).replace(/^ /, '');
    if (field === 'event') {
      eventName = value;
    } else if (field === 'data') {
      dataLines.push(value);
    }
  }

  if (dataLines.length === 0) {
    return;
  }

  onEvent(parseAssistantStreamEvent(eventName, dataLines.join('\n')));
}

function parseAssistantStreamEvent(eventName: string, rawData: string): AssistantStreamEvent {
  const data = JSON.parse(rawData) as unknown;
  if (!isRecord(data)) {
    throw new Error('Érvénytelen streaming esemény érkezett.');
  }

  if (eventName === 'start' && typeof data.chat_id === 'number') {
    return { event: 'start', data: { chat_id: data.chat_id } };
  }
  if ((eventName === 'delta' || eventName === 'reasoning_delta') && typeof data.content === 'string') {
    return { event: eventName, data: { content: data.content } };
  }
  if (eventName === 'tool_activity' && typeof data.content === 'string') {
    return { event: 'tool_activity', data: { content: data.content, raw: data.raw } };
  }
  if (eventName === 'status') {
    return { event: 'status', data: { raw: data.raw } };
  }
  if (eventName === 'error' && typeof data.message === 'string') {
    return { event: 'error', data: { message: data.message } };
  }
  if (eventName === 'done' && isAssistantChatDetail(data.chat)) {
    return { event: 'done', data: { chat: data.chat } };
  }

  throw new Error('Ismeretlen vagy hiányos streaming esemény érkezett: ' + eventName);
}

function isAssistantChatDetail(value: unknown): value is AssistantChatDetail {
  return isRecord(value) && typeof value.id === 'number' && Array.isArray(value.messages);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
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
