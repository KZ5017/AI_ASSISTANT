import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Lightbulb, LightbulbOff, Moon, MoreVertical, Pencil, Plus, RefreshCw, RotateCcw, Send, Square, Sun, Trash2, X } from "lucide-react";

import {
  type AssistantChatDetail,
  type AssistantChatSummary,
  type AssistantMessage,
  type AssistantReasoningMode,
  type LMStudioHealth,
  createAssistantChat,
  deleteAssistantChat,
  fetchLMStudioHealth,
  fetchLMStudioModels,
  getAssistantChat,
  listAssistantChats,
  loadLMStudioChatModel,
  renameAssistantChat,
  selectLMStudioChatModel,
  streamAssistantMessage,
  streamRegenerateAssistantMessage,
  streamRetryLastUserMessage,
  unloadLMStudioChatModel,
  updateAssistantMessage,
} from "../api/assistant";

type ChatShellProps = {
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
};

type PendingMessage = Pick<AssistantMessage, "role" | "content" | "sequence_index"> & { id: "pending-user" | "pending-assistant" };

const MAX_CONTEXT_CHARS = 120000;

export function ChatShell({ theme, onThemeChange }: ChatShellProps) {
  const [chats, setChats] = useState<AssistantChatSummary[]>([]);
  const [activeChat, setActiveChat] = useState<AssistantChatDetail | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isRetryingLastUser, setIsRetryingLastUser] = useState(false);
  const [isSavingRecoveryEdit, setIsSavingRecoveryEdit] = useState(false);
  const [reasoningEnabled, setReasoningEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingUser, setPendingUser] = useState<PendingMessage | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<PendingMessage | null>(null);
  const [regeneratingAssistantId, setRegeneratingAssistantId] = useState<number | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);
  const [editingUserMessageId, setEditingUserMessageId] = useState<number | null>(null);
  const [editingUserContent, setEditingUserContent] = useState("");
  const [openMenuChatId, setOpenMenuChatId] = useState<number | null>(null);
  const [conversationMenuPosition, setConversationMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const [renameTarget, setRenameTarget] = useState<AssistantChatSummary | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AssistantChatSummary | null>(null);
  const [lmHealth, setLmHealth] = useState<LMStudioHealth | null>(null);
  const [lmModels, setLmModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [isModelBusy, setIsModelBusy] = useState(false);
  const [modelNotice, setModelNotice] = useState<string | null>(null);
  const messageThreadRef = useRef<HTMLDivElement | null>(null);
  const composerTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const recoveryEditorTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const streamAbortControllerRef = useRef<AbortController | null>(null);

  const activeMessages = useMemo(() => {
    const messages: Array<AssistantMessage | PendingMessage> = regeneratingAssistantId
      ? (activeChat?.messages ?? []).filter((message) => message.id !== regeneratingAssistantId)
      : (activeChat?.messages ?? []);
    return [...messages, ...(pendingUser ? [pendingUser] : []), ...(pendingAssistant ? [pendingAssistant] : [])];
  }, [activeChat, pendingUser, pendingAssistant, regeneratingAssistantId]);
  const latestAssistantId = [...(activeChat?.messages ?? [])].reverse().find((message) => message.role === "assistant")?.id;
  const persistedMessages = activeChat?.messages ?? [];
  const latestPersistedMessage = persistedMessages.length > 0 ? persistedMessages[persistedMessages.length - 1] : undefined;
  const unansweredLastUserId = latestPersistedMessage?.role === "user" ? latestPersistedMessage.id : null;
  const trimmedInput = input.trim();
  const contextCharCount = activeMessages.reduce((total, message) => total + message.content.length, 0) + trimmedInput.length;
  const isPromptTooLong = input.length >= MAX_CONTEXT_CHARS;
  const isContextTooLong = contextCharCount > MAX_CONTEXT_CHARS;
  const selectedModelLoaded = lmHealth?.selected_chat_model_loaded === true;
  const selectedModelAvailable = lmHealth?.selected_chat_model_available !== false;
  const isStreaming = isSending || isRegenerating || isRetryingLastUser;
  const isAssistantBusy = isStreaming || isSavingRecoveryEdit;
  const canSend = trimmedInput !== "" && !isAssistantBusy && !isPromptTooLong && !isContextTooLong && selectedModelLoaded;
  const composerWarningText = isPromptTooLong
    ? "A prompt elérte a 120000 karakteres limitet."
    : isContextTooLong
      ? "A teljes beszélgetés és az új üzenet meghaladja a 120000 karakteres kontextuskeretet."
      : !selectedModelLoaded
        ? "Válassz ki és tölts be egy chat modellt az üzenetküldéshez."
        : "";

  useEffect(() => {
    void refreshChats();
    void refreshModelState();
  }, []);

  useEffect(() => {
    const element = messageThreadRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [activeMessages, isSending]);

  useEffect(() => {
    resizeComposerTextarea(composerTextareaRef.current);
  }, [input]);

  useEffect(() => {
    resizeRecoveryEditorTextarea(recoveryEditorTextareaRef.current);
  }, [editingUserContent, editingUserMessageId]);

  useEffect(() => {
    function handleDocumentMouseDown(event: MouseEvent) {
      const target = event.target;
      if (target instanceof Element && target.closest(".conversation-row")) {
        return;
      }
      setOpenMenuChatId(null);
      setConversationMenuPosition(null);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenMenuChatId(null);
        setConversationMenuPosition(null);
        setRenameTarget(null);
        setDeleteTarget(null);
      }
    }

    document.addEventListener("mousedown", handleDocumentMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleDocumentMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  async function refreshChats(selectChatId?: number | null) {
    setIsLoading(true);
    setError(null);
    try {
      const result = await listAssistantChats();
      setChats(result.chats);
      const targetId = selectChatId === null ? result.chats[0]?.id : (selectChatId ?? activeChat?.id ?? result.chats[0]?.id);
      if (targetId) {
        setActiveChat(await getAssistantChat(targetId));
      } else {
        setActiveChat(null);
      }
    } catch (exc) {
      setError(errorMessage(exc));
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshModelState() {
    setModelNotice(null);
    try {
      const [health, models] = await Promise.all([fetchLMStudioHealth(), fetchLMStudioModels()]);
      setLmHealth(health);
      setLmModels(models.models);
      setSelectedModel(health.selected_chat_model || models.selected_chat_model || models.configured_chat_model || models.models[0] || "");
    } catch (exc) {
      setLmHealth(null);
      setModelNotice(errorMessage(exc));
    }
  }

  async function handleSelectModel(modelId: string) {
    setSelectedModel(modelId);
    setIsModelBusy(true);
    setModelNotice(null);
    try {
      await selectLMStudioChatModel(modelId);
      await refreshModelState();
    } catch (exc) {
      setModelNotice(errorMessage(exc));
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
      setModelNotice("Betöltve: " + result.instance_id);
      await refreshModelState();
    } catch (exc) {
      setModelNotice(errorMessage(exc));
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
      setModelNotice("Leválasztva: " + result.instance_id);
      await refreshModelState();
    } catch (exc) {
      setModelNotice(errorMessage(exc));
    } finally {
      setIsModelBusy(false);
    }
  }

  async function handleCreateChat() {
    setError(null);
    try {
      const chat = await createAssistantChat({ reasoning_mode: reasoningMode() });
      setActiveChat(chat);
      await refreshChats(chat.id);
    } catch (exc) {
      setError(errorMessage(exc));
    }
  }

  async function handleSelectChat(chatId: number) {
    setOpenMenuChatId(null);
    setConversationMenuPosition(null);
    setError(null);
    try {
      setActiveChat(await getAssistantChat(chatId));
    } catch (exc) {
      setError(errorMessage(exc));
    }
  }

  async function handleSend(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!canSend) {
      return;
    }
    const outgoing = trimmedInput;
    const mode = reasoningMode();
    let chat = activeChat;
    let streamStarted = false;
    const abortController = new AbortController();
    streamAbortControllerRef.current = abortController;
    setIsSending(true);
    setError(null);
    setInput("");

    try {
      if (!chat) {
        chat = await createAssistantChat({ reasoning_mode: mode });
        setActiveChat(chat);
      }

      const nextSequence = chat.messages.length;
      setPendingUser({ id: "pending-user", role: "user", content: outgoing, sequence_index: nextSequence });
      setPendingAssistant({ id: "pending-assistant", role: "assistant", content: "", sequence_index: nextSequence + 1 });

      const updated = await streamAssistantMessage(
        chat.id,
        { content: outgoing, reasoning_mode: mode },
        {
          signal: abortController.signal,
          handlers: {
            onStart: () => {
              streamStarted = true;
            },
            onDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, content: current.content + content } : current);
            },
            onError: (message) => {
              setError(message);
            },
          },
        },
      );
      setActiveChat(updated);
      setPendingUser(null);
      setPendingAssistant(null);
      await refreshChats(updated.id);
      await refreshModelState();
    } catch (exc) {
      const aborted = isAbortError(exc);
      if (!aborted) {
        setError(errorMessage(exc));
      }
      setPendingUser(null);
      setPendingAssistant(null);
      if (chat && (streamStarted || aborted)) {
        try {
          const refreshed = await getAssistantChat(chat.id);
          setActiveChat(refreshed);
          await refreshChats(refreshed.id);
        } catch {
          // Keep the visible error from the stream failure.
        }
      } else {
        setInput(outgoing);
      }
    } finally {
      if (streamAbortControllerRef.current === abortController) {
        streamAbortControllerRef.current = null;
      }
      setIsSending(false);
    }
  }

  function handleComposerKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    void handleSend();
  }

  async function handleRetryLastUser(chatOverride?: AssistantChatDetail) {
    const targetChat = chatOverride ?? activeChat;
    const latestUser = targetChat?.messages[targetChat.messages.length - 1];
    if (!targetChat || !latestUser || latestUser.role !== "user" || isStreaming || isSavingRecoveryEdit || !selectedModelLoaded) {
      return;
    }
    let streamStarted = false;
    const abortController = new AbortController();
    streamAbortControllerRef.current = abortController;
    setIsRetryingLastUser(true);
    setError(null);
    setPendingAssistant({ id: "pending-assistant", role: "assistant", content: "", sequence_index: latestUser.sequence_index + 1 });

    try {
      const updated = await streamRetryLastUserMessage(
        targetChat.id,
        { reasoning_mode: reasoningMode() },
        {
          signal: abortController.signal,
          handlers: {
            onStart: () => {
              streamStarted = true;
            },
            onDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, content: current.content + content } : current);
            },
            onError: (message) => {
              setError(message);
            },
          },
        },
      );
      setActiveChat(updated);
      setPendingAssistant(null);
      await refreshChats(updated.id);
      await refreshModelState();
    } catch (exc) {
      const aborted = isAbortError(exc);
      if (!aborted) {
        setError(errorMessage(exc));
      }
      setPendingAssistant(null);
      if (streamStarted || aborted) {
        try {
          const refreshed = await getAssistantChat(targetChat.id);
          setActiveChat(refreshed);
          await refreshChats(refreshed.id);
        } catch {
          // Keep the visible error from the stream failure.
        }
      }
    } finally {
      if (streamAbortControllerRef.current === abortController) {
        streamAbortControllerRef.current = null;
      }
      setIsRetryingLastUser(false);
    }
  }


  function handleStartEditLastUser(message: AssistantMessage) {
    if (isAssistantBusy) {
      return;
    }
    setError(null);
    setEditingUserMessageId(message.id);
    setEditingUserContent(message.content);
  }

  function handleCancelEditLastUser() {
    setEditingUserMessageId(null);
    setEditingUserContent("");
  }

  function handleRecoveryEditorKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
    }
  }

  async function handleSaveAndSendEditedLastUser() {
    if (!activeChat || !editingUserMessageId || isAssistantBusy || !selectedModelLoaded) {
      return;
    }
    const content = editingUserContent.trim();
    if (content === "") {
      setError("Az üzenet nem lehet üres.");
      return;
    }

    setIsSavingRecoveryEdit(true);
    setError(null);
    try {
      const updated = await updateAssistantMessage(activeChat.id, editingUserMessageId, { content });
      setActiveChat(updated);
      setEditingUserMessageId(null);
      setEditingUserContent("");
      await refreshChats(updated.id);
      await handleRetryLastUser(updated);
    } catch (exc) {
      setError(errorMessage(exc));
    } finally {
      setIsSavingRecoveryEdit(false);
    }
  }


  async function handleRegenerate() {
    if (!activeChat || !latestAssistantId || isRegenerating || isSending || !selectedModelLoaded) {
      return;
    }
    const latestAssistant = [...activeChat.messages].reverse().find((message) => message.id === latestAssistantId);
    if (!latestAssistant) {
      return;
    }
    let streamStarted = false;
    const abortController = new AbortController();
    streamAbortControllerRef.current = abortController;
    setIsRegenerating(true);
    setError(null);
    setRegeneratingAssistantId(latestAssistant.id);
    setPendingAssistant({ id: "pending-assistant", role: "assistant", content: "", sequence_index: latestAssistant.sequence_index });

    try {
      const updated = await streamRegenerateAssistantMessage(
        activeChat.id,
        { reasoning_mode: reasoningMode() },
        {
          signal: abortController.signal,
          handlers: {
            onStart: () => {
              streamStarted = true;
            },
            onDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, content: current.content + content } : current);
            },
            onError: (message) => {
              setError(message);
            },
          },
        },
      );
      setActiveChat(updated);
      setPendingAssistant(null);
      setRegeneratingAssistantId(null);
      await refreshChats(updated.id);
      await refreshModelState();
    } catch (exc) {
      const aborted = isAbortError(exc);
      if (!aborted) {
        setError(errorMessage(exc));
      }
      setPendingAssistant(null);
      setRegeneratingAssistantId(null);
      if (streamStarted || aborted) {
        try {
          const refreshed = await getAssistantChat(activeChat.id);
          setActiveChat(refreshed);
          await refreshChats(refreshed.id);
        } catch {
          // Keep the visible error from the stream failure.
        }
      }
    } finally {
      if (streamAbortControllerRef.current === abortController) {
        streamAbortControllerRef.current = null;
      }
      setIsRegenerating(false);
    }
  }

  async function handleCopy(message: AssistantMessage) {
    await navigator.clipboard.writeText(message.content);
    setCopiedMessageId(message.id);
    window.setTimeout(() => setCopiedMessageId(null), 1200);
  }

  async function handleRenameSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!renameTarget || renameTitle.trim() === "") {
      return;
    }
    try {
      const updated = await renameAssistantChat(renameTarget.id, renameTitle.trim());
      setActiveChat((current) => (current?.id === updated.id ? updated : current));
      setRenameTarget(null);
      setRenameTitle("");
      await refreshChats(updated.id);
    } catch (exc) {
      setError(errorMessage(exc));
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) {
      return;
    }
    try {
      await deleteAssistantChat(deleteTarget.id);
      const deletedActive = activeChat?.id === deleteTarget.id;
      setDeleteTarget(null);
      setOpenMenuChatId(null);
      setConversationMenuPosition(null);
      if (deletedActive) {
        setActiveChat(null);
      }
      await refreshChats(deletedActive ? null : undefined);
    } catch (exc) {
      setError(errorMessage(exc));
    }
  }

  function handleConversationMenuToggle(chatId: number, event: React.MouseEvent<HTMLButtonElement>) {
    if (openMenuChatId === chatId) {
      setOpenMenuChatId(null);
      setConversationMenuPosition(null);
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const menuWidth = 160;
    const viewportPadding = 8;
    setConversationMenuPosition({
      top: rect.bottom + 6,
      left: Math.min(Math.max(viewportPadding, rect.right - menuWidth), window.innerWidth - menuWidth - viewportPadding),
    });
    setOpenMenuChatId(chatId);
  }

  function openRename(chat: AssistantChatSummary) {
    setOpenMenuChatId(null);
    setConversationMenuPosition(null);
    setRenameTarget(chat);
    setRenameTitle(chat.title);
  }

  function handleStopStream() {
    streamAbortControllerRef.current?.abort();
  }

  function reasoningMode(): AssistantReasoningMode {
    return reasoningEnabled ? "model_default" : "normal";
  }

  return (
    <section className="chat-shell" aria-label="Lokális AI chat">
      <aside className="conversation-rail">
        <div className="rail-header">
          <button className="primary-action" type="button" onClick={handleCreateChat} disabled={isSending || isLoading}>
            <Plus size={18} aria-hidden="true" />
            Új chat
          </button>
          <button className="icon-button" type="button" aria-label="Beszélgetések frissítése" onClick={() => void refreshChats()}>
            <RefreshCw size={18} aria-hidden="true" />
          </button>
        </div>

        <nav className="conversation-list" aria-label="Mentett beszélgetések">
          {chats.map((chat) => (
            <div className="conversation-row" key={chat.id}>
              <button className={"conversation-item " + (activeChat?.id === chat.id ? "is-active" : "")} type="button" title={chat.title} onClick={() => void handleSelectChat(chat.id)}>
                <span>{chat.title}</span>
              </button>
              <button className="conversation-menu-button" type="button" aria-label="Beszélgetés menü" onClick={(event) => handleConversationMenuToggle(chat.id, event)}>
                <MoreVertical size={16} aria-hidden="true" />
              </button>
              {openMenuChatId === chat.id ? (
                <div className="conversation-menu" style={conversationMenuPosition ?? undefined}>
                  <button type="button" onClick={() => openRename(chat)}><Pencil size={15} aria-hidden="true" /> Átnevezés</button>
                  <button type="button" className="danger-menu-item" onClick={() => { setOpenMenuChatId(null); setConversationMenuPosition(null); setDeleteTarget(chat); }}><Trash2 size={15} aria-hidden="true" /> Törlés</button>
                </div>
              ) : null}
            </div>
          ))}
          {!isLoading && chats.length === 0 ? <p className="rail-empty">Nincs mentett beszélgetés.</p> : null}
        </nav>
      </aside>

      <section className="chat-canvas">
        <ModelPanel
          chatTitle={activeChat?.title ?? "Local AI Assistant"}
          health={lmHealth}
          models={lmModels}
          selectedModel={selectedModel}
          selectedModelAvailable={selectedModelAvailable}
          selectedModelLoaded={selectedModelLoaded}
          isBusy={isModelBusy}
          notice={modelNotice}
          theme={theme}
          onThemeChange={onThemeChange}
          onRefresh={() => void refreshModelState()}
          onSelect={(modelId) => void handleSelectModel(modelId)}
          onLoad={() => void handleLoadModel()}
          onUnload={() => void handleUnloadModel()}
        />

        {error ? <ErrorBanner message={error} onClose={() => setError(null)} /> : null}

        {activeMessages.length === 0 ? (
          <div className="empty-thread">
            <p className="empty-title">Miben segíthetek?</p>
            <p className="empty-copy">Indíts új beszélgetést, vagy írj rögtön egy üzenetet. Minden lokálisan fut az LM Studio mögött.</p>
          </div>
        ) : (
          <div className="message-thread" aria-live="polite" ref={messageThreadRef}>
            {activeMessages.map((message) => (
              <article className={"message-row is-" + message.role} key={message.id}>
                <div className={"message-bubble " + (message.role === "user" && message.id === editingUserMessageId ? "is-editing" : "")}>
                  {message.role === "assistant" ? (
                    message.id === "pending-assistant" && message.content === "" ? <TypingIndicator /> : <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                  ) : message.id === editingUserMessageId ? (
                    <textarea ref={recoveryEditorTextareaRef} value={editingUserContent} maxLength={MAX_CONTEXT_CHARS} rows={1} aria-label="User üzenet szerkesztése" onChange={(event) => setEditingUserContent(event.target.value)} onKeyDown={handleRecoveryEditorKeyDown} autoFocus />
                  ) : <p>{message.content}</p>}
                </div>
                {message.role === "assistant" && typeof message.id === "number" ? (
                  <div className="message-actions">
                    <button type="button" onClick={() => void handleCopy(message)} aria-label="Válasz másolása"><Copy size={15} aria-hidden="true" /> {copiedMessageId === message.id ? "Másolva" : "Másolás"}</button>
                    {message.id === latestAssistantId ? <button type="button" onClick={handleRegenerate} disabled={isStreaming || !selectedModelLoaded} aria-label="Válasz újragenerálása"><RotateCcw size={15} aria-hidden="true" /> Újragenerálás</button> : null}
                  </div>
                ) : null}
                {message.role === "user" && typeof message.id === "number" && message.id === unansweredLastUserId && !pendingAssistant ? (
                  <div className="message-actions">
                    {message.id === editingUserMessageId ? (
                      <>
                        <button type="button" onClick={() => void handleSaveAndSendEditedLastUser()} disabled={isAssistantBusy || !selectedModelLoaded || editingUserContent.trim() === ""} aria-label="Szerkesztett üzenet mentése és küldése"><Send size={15} aria-hidden="true" /> Mentés és küldés</button>
                        <button type="button" onClick={handleCancelEditLastUser} disabled={isAssistantBusy} aria-label="Szerkesztés megszakítása"><X size={15} aria-hidden="true" /> Mégse</button>
                      </>
                    ) : (
                      <>
                        <button type="button" onClick={() => handleStartEditLastUser(message)} disabled={isAssistantBusy} aria-label="Üzenet szerkesztése"><Pencil size={15} aria-hidden="true" /> Szerkesztés</button>
                        <button type="button" onClick={() => void handleRetryLastUser()} disabled={isAssistantBusy || !selectedModelLoaded} aria-label="Üzenet újraküldése"><Send size={15} aria-hidden="true" /> Újraküldés</button>
                      </>
                    )}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}

        <form className="composer" aria-label="Üzenet küldése" onSubmit={handleSend}>
          <div className="composer-input-slot">
            <textarea ref={composerTextareaRef} rows={1} maxLength={MAX_CONTEXT_CHARS} placeholder="Írj üzenetet..." aria-label="Üzenet szövege" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleComposerKeyDown} />
          </div>
          <button className={"reasoning-toggle " + (reasoningEnabled ? "is-active" : "")} type="button" aria-pressed={reasoningEnabled} onClick={() => setReasoningEnabled((value) => !value)} title={reasoningEnabled ? "Gondolkodó mód bekapcsolva" : "Gondolkodó mód kikapcsolva"}>
            {reasoningEnabled ? <Lightbulb size={17} aria-hidden="true" /> : <LightbulbOff size={17} aria-hidden="true" />}
            Gondolkodó
          </button>
          <button className="send-button" type={isStreaming ? "button" : "submit"} disabled={!isStreaming && !canSend} onClick={isStreaming ? handleStopStream : undefined}>
            {isStreaming ? <Square size={16} aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
            {isStreaming ? "Leállítás" : "Küldés"}
          </button>
          <p className={"composer-warning " + (composerWarningText ? "" : "is-hidden")} aria-live="polite" aria-hidden={composerWarningText ? undefined : true}>
            {composerWarningText || "Figyelmeztetés helye"}
          </p>
        </form>
      </section>

      {renameTarget ? (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setRenameTarget(null)}>
          <form className="app-dialog" aria-label="Beszélgetés átnevezése" onSubmit={handleRenameSubmit} onMouseDown={(event) => event.stopPropagation()}>
            <h2>Átnevezés</h2>
            <input value={renameTitle} onChange={(event) => setRenameTitle(event.target.value)} maxLength={120} autoFocus />
            <div className="dialog-actions">
              <button type="button" className="secondary-action" onClick={() => setRenameTarget(null)}>Mégse</button>
              <button type="submit" className="primary-action">Mentés</button>
            </div>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setDeleteTarget(null)}>
          <div className="app-dialog" role="dialog" aria-modal="true" aria-label="Beszélgetés törlése" onMouseDown={(event) => event.stopPropagation()}>
            <h2>Törlés</h2>
            <p>Biztosan törlöd ezt a beszélgetést? A törlés soft delete-ként történik.</p>
            <div className="dialog-actions">
              <button type="button" className="secondary-action" onClick={() => setDeleteTarget(null)}>Mégse</button>
              <button type="button" className="danger-action" onClick={() => void handleDeleteConfirm()}>Törlés</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ModelPanel({
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
}: {
  chatTitle: string;
  health: LMStudioHealth | null;
  models: string[];
  selectedModel: string;
  selectedModelAvailable: boolean;
  selectedModelLoaded: boolean;
  isBusy: boolean;
  notice: string | null;
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
  onRefresh: () => void;
  onSelect: (modelId: string) => void;
  onLoad: () => void;
  onUnload: () => void;
}) {
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
        <p className="eyebrow">Modell állapot</p>
        <div className="model-status-line">
          <span className={"status-dot " + (selectedModelLoaded ? "is-ok" : "is-warning")} />
          <strong>{statusText}</strong>
          <span>{health?.base_url ?? "LM Studio"}</span>
        </div>
        <h1 className="model-chat-title">{chatTitle}</h1>
      </div>

      <div className="model-controls">
        <label className="model-select-label">
          <span>Chat modell</span>
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
      {health?.error_message ? <p className="model-warning">{health.error_message}</p> : null}
      {notice ? <p className="model-notice">{notice}</p> : null}
    </section>
  );
}

function ErrorBanner({ message, onClose }: { message: string; onClose: () => void }) {
  return <div className="error-banner" role="alert">{message}<button type="button" aria-label="Hiba bezárása" onClick={onClose}><X size={16} aria-hidden="true" /></button></div>;
}

function TypingIndicator() {
  return <div className="typing-indicator" aria-label="Az asszisztens válaszol"><span /><span /><span /></div>;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Váratlan hiba történt.";
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

function resizeComposerTextarea(element: HTMLTextAreaElement | null) {
  resizeTextareaToContent(element, 180);
}

function resizeRecoveryEditorTextarea(element: HTMLTextAreaElement | null) {
  resizeTextareaToContent(element, 260);
}

function resizeTextareaToContent(element: HTMLTextAreaElement | null, maxHeight: number) {
  if (!element) {
    return;
  }
  element.style.height = "auto";
  const nextHeight = Math.min(element.scrollHeight, maxHeight);
  element.style.height = nextHeight + "px";
  element.style.overflowY = element.scrollHeight > maxHeight ? "auto" : "hidden";
  element.style.overflowX = "hidden";
}
