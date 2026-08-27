import { type CSSProperties, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";
import {
  type AssistantChatDetail,
  type AssistantChatSummary,
  type AssistantMessage,
  type AssistantReasoningMode,
  type AssistantToolMode,
  createAssistantChat,
  deleteAssistantChat,
  getAssistantChat,
  listAssistantChats,
  renameAssistantChat,
  streamAssistantMessage,
  streamRegenerateAssistantMessage,
  streamRetryLastUserMessage,
  updateAssistantMessage,
} from "../api/assistant";
import { ChatDialogs } from "./ChatDialogs";
import { Composer } from "./Composer";
import { ConversationRail } from "./ConversationRail";
import { ErrorBanner } from "./ErrorBanner";
import { MessageThread } from "./MessageThread";
import { ModelPanel } from "./ModelPanel";
import { type PendingMessage } from "./chatTypes";
import { useAutosizeTextarea } from "../hooks/useAutosizeTextarea";
import { useModelState } from "../hooks/useModelState";
import { useThreadScrollFollow } from "../hooks/useThreadScrollFollow";
import { useStableCallback } from "../hooks/useStableCallback";
import { computeComposerWarning, normalizeErrorMessage } from "../utils/notices";

type ChatShellProps = {
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
};

const MAX_CONTEXT_CHARS = 120000;

function toolModeSupportsReasoning(toolMode: AssistantToolMode): boolean {
  return toolMode === "none" || toolMode === "graphrag";
}

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
  const [activeToolMode, setActiveToolMode] = useState<AssistantToolMode>("none");
  const [error, setError] = useState<string | null>(null);
  const [pendingUser, setPendingUser] = useState<PendingMessage | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<PendingMessage | null>(null);
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);
  const [regeneratingAssistantId, setRegeneratingAssistantId] = useState<number | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);
  const [editingUserMessageId, setEditingUserMessageId] = useState<number | null>(null);
  const [editingUserContent, setEditingUserContent] = useState("");
  const [openMenuChatId, setOpenMenuChatId] = useState<number | null>(null);
  const [conversationMenuPosition, setConversationMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const [renameTarget, setRenameTarget] = useState<AssistantChatSummary | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AssistantChatSummary | null>(null);
  const {
    lmHealth,
    selectedModel,
    selectedModelLoaded,
    refreshModelState,
  } = useModelState();
  const composerTextareaRef = useAutosizeTextarea(180, [input]);
  const [composerTextareaHeight, setComposerTextareaHeight] = useState(50);
  const recoveryEditorTextareaRef = useAutosizeTextarea(260, [editingUserContent, editingUserMessageId]);
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
  const historyCharCount = useMemo(() => activeMessages.reduce((total, message) => total + message.content.length, 0), [activeMessages]);
  const contextCharCount = historyCharCount + trimmedInput.length;
  const isPromptTooLong = input.length >= MAX_CONTEXT_CHARS;
  const isContextTooLong = contextCharCount > MAX_CONTEXT_CHARS;
  const isStreaming = isSending || isRegenerating || isRetryingLastUser;
  const isAssistantBusy = isStreaming || isSavingRecoveryEdit;
  const canSend = trimmedInput !== "" && !isAssistantBusy && !isPromptTooLong && !isContextTooLong && selectedModelLoaded;
  const composerWarningText = computeComposerWarning({ isPromptTooLong, isContextTooLong, selectedModelLoaded });
  const { threadRef: messageThreadRef, handleThreadScroll, resetThreadScrollFollow, scrollThreadToBottom, isThreadAtBottom } = useThreadScrollFollow([activeMessages, isStreaming], [activeChat?.id]);

  useEffect(() => {
    void refreshChats();
  }, []);

  useEffect(() => {
    if (editingUserMessageId || renameTarget || deleteTarget || isAssistantBusy) {
      return;
    }
    window.requestAnimationFrame(() => {
      composerTextareaRef.current?.focus();
    });
  }, [activeChat?.id, editingUserMessageId, renameTarget, deleteTarget, isAssistantBusy, composerTextareaRef]);

  useEffect(() => {
    const element = composerTextareaRef.current;
    if (!element) {
      return;
    }

    const updateHeight = () => setComposerTextareaHeight(element.offsetHeight || 50);
    updateHeight();

    const observer = new ResizeObserver(updateHeight);
    observer.observe(element);
    return () => observer.disconnect();
  }, [composerTextareaRef]);

  useLayoutEffect(() => {
    if (!editingUserMessageId || !isThreadAtBottom) {
      return;
    }
    scrollThreadToBottom();
  }, [editingUserContent, editingUserMessageId, isThreadAtBottom, scrollThreadToBottom]);

  const threadFrameStyle = { "--composer-textarea-height": composerTextareaHeight + "px" } as CSSProperties;
  const handleMessageThreadScroll = useStableCallback(handleThreadScroll);
  const handleMessageCopy = useStableCallback((message: AssistantMessage) => {
    void handleCopy(message);
  });
  const handleMessageRegenerate = useStableCallback(() => {
    void handleRegenerate();
  });
  const handleMessageStartEditLastUser = useStableCallback((message: AssistantMessage) => {
    handleStartEditLastUser(message);
  });
  const handleMessageRecoveryEditorKeyDown = useStableCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    handleRecoveryEditorKeyDown(event);
  });
  const handleMessageSaveAndSendEditedLastUser = useStableCallback(() => {
    void handleSaveAndSendEditedLastUser();
  });
  const handleMessageCancelEditLastUser = useStableCallback(() => {
    handleCancelEditLastUser();
  });
  const handleMessageRetryLastUser = useStableCallback(() => {
    void handleRetryLastUser();
  });
  const handleMessageReasoningToggle = useStableCallback(() => {
    setIsReasoningOpen((value) => !value);
  });


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

  async function refreshChats(selectChatId?: number | null, { clearError = true }: { clearError?: boolean } = {}) {
    setIsLoading(true);
    if (clearError) {
      setError(null);
    }
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
      setError(normalizeErrorMessage(exc));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateChat() {
    setError(null);
    try {
      const chat = await createAssistantChat({ reasoning_mode: reasoningMode() });
      setActiveChat(chat);
      await refreshChats(chat.id);
    } catch (exc) {
      setError(normalizeErrorMessage(exc));
    }
  }

  async function handleSelectChat(chatId: number) {
    setOpenMenuChatId(null);
    setConversationMenuPosition(null);
    setError(null);
    try {
      setActiveChat(await getAssistantChat(chatId));
    } catch (exc) {
      setError(normalizeErrorMessage(exc));
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
    resetThreadScrollFollow();
    setError(null);
    setInput("");

    try {
      if (!chat) {
        chat = await createAssistantChat({ reasoning_mode: mode });
        setActiveChat(chat);
      }

      const nextSequence = chat.messages.length;
      setPendingUser({ id: "pending-user", role: "user", content: outgoing, sequence_index: nextSequence });
      setIsReasoningOpen(false);
      setPendingAssistant({ id: "pending-assistant", role: "assistant", content: "", reasoningContent: "", toolActivityContent: "", sequence_index: nextSequence + 1 });

      const updated = await streamAssistantMessage(
        chat.id,
        { content: outgoing, reasoning_mode: mode, tool_mode: activeToolMode },
        {
          signal: abortController.signal,
          handlers: {
            onStart: () => {
              streamStarted = true;
            },
            onDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, content: current.content + content } : current);
            },
            onReasoningDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, reasoningContent: (current.reasoningContent ?? "") + content } : current);
            },
            onToolActivity: (content) => {
              setPendingAssistant((current) => current ? { ...current, toolActivityContent: (current.toolActivityContent ?? "") + content } : current);
            },
            onError: (message) => {
              setError(normalizeErrorMessage(message));
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
        setError(normalizeErrorMessage(exc));
      }
      setPendingUser(null);
      setPendingAssistant(null);
      if (chat && (streamStarted || aborted)) {
        try {
          const refreshed = await getAssistantChat(chat.id);
          setActiveChat(refreshed);
          await refreshChats(refreshed.id, { clearError: false });
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
    resetThreadScrollFollow();
    setError(null);
    setIsReasoningOpen(false);
    setPendingAssistant({ id: "pending-assistant", role: "assistant", content: "", reasoningContent: "", toolActivityContent: "", sequence_index: latestUser.sequence_index + 1 });

    try {
      const updated = await streamRetryLastUserMessage(
        targetChat.id,
        { reasoning_mode: reasoningMode(), tool_mode: activeToolMode },
        {
          signal: abortController.signal,
          handlers: {
            onStart: () => {
              streamStarted = true;
            },
            onDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, content: current.content + content } : current);
            },
            onReasoningDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, reasoningContent: (current.reasoningContent ?? "") + content } : current);
            },
            onToolActivity: (content) => {
              setPendingAssistant((current) => current ? { ...current, toolActivityContent: (current.toolActivityContent ?? "") + content } : current);
            },
            onError: (message) => {
              setError(normalizeErrorMessage(message));
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
        setError(normalizeErrorMessage(exc));
      }
      setPendingAssistant(null);
      if (streamStarted || aborted) {
        try {
          const refreshed = await getAssistantChat(targetChat.id);
          setActiveChat(refreshed);
          await refreshChats(refreshed.id, { clearError: false });
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
      setError(normalizeErrorMessage(exc));
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
    resetThreadScrollFollow();
    setError(null);
    setRegeneratingAssistantId(latestAssistant.id);
    setIsReasoningOpen(false);
    setPendingAssistant({ id: "pending-assistant", role: "assistant", content: "", reasoningContent: "", toolActivityContent: "", sequence_index: latestAssistant.sequence_index });

    try {
      const updated = await streamRegenerateAssistantMessage(
        activeChat.id,
        { reasoning_mode: reasoningMode(), tool_mode: activeToolMode },
        {
          signal: abortController.signal,
          handlers: {
            onStart: () => {
              streamStarted = true;
            },
            onDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, content: current.content + content } : current);
            },
            onReasoningDelta: (content) => {
              setPendingAssistant((current) => current ? { ...current, reasoningContent: (current.reasoningContent ?? "") + content } : current);
            },
            onToolActivity: (content) => {
              setPendingAssistant((current) => current ? { ...current, toolActivityContent: (current.toolActivityContent ?? "") + content } : current);
            },
            onError: (message) => {
              setError(normalizeErrorMessage(message));
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
        setError(normalizeErrorMessage(exc));
      }
      setPendingAssistant(null);
      setRegeneratingAssistantId(null);
      if (streamStarted || aborted) {
        try {
          const refreshed = await getAssistantChat(activeChat.id);
          setActiveChat(refreshed);
          await refreshChats(refreshed.id, { clearError: false });
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
      setError(normalizeErrorMessage(exc));
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
      setError(normalizeErrorMessage(exc));
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
    const menuHeight = 96;
    const menuGap = 6;
    const viewportPadding = 8;
    const menuTopBelow = rect.bottom + menuGap;
    const menuTopAbove = rect.top - menuHeight - menuGap;
    const top = menuTopBelow + menuHeight > window.innerHeight - viewportPadding
      ? Math.max(viewportPadding, menuTopAbove)
      : menuTopBelow;
    setConversationMenuPosition({
      top,
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
    return reasoningEnabled && toolModeSupportsReasoning(activeToolMode)
      ? "model_default"
      : "normal";
  }

  function handleReasoningToggle() {
    if (toolModeSupportsReasoning(activeToolMode)) {
      setReasoningEnabled((value) => !value);
    }
  }

  function handleToolModeToggle(toolMode: AssistantToolMode) {
    const nextToolMode = activeToolMode === toolMode ? "none" : toolMode;
    setActiveToolMode(nextToolMode);
    if (!toolModeSupportsReasoning(nextToolMode)) {
      setReasoningEnabled(false);
    }
  }

  return (
    <section className="chat-shell" aria-label="Lokális AI chat">
      <ConversationRail
        chats={chats}
        activeChatId={activeChat?.id ?? null}
        isLoading={isLoading}
        isSending={isSending}
        health={lmHealth}
        selectedModelLoaded={selectedModelLoaded}
        openMenuChatId={openMenuChatId}
        conversationMenuPosition={conversationMenuPosition}
        onCreateChat={() => void handleCreateChat()}
        onRefresh={() => {
          void refreshChats(undefined, { clearError: false });
          void refreshModelState();
        }}
        onSelectChat={(chatId) => void handleSelectChat(chatId)}
        onMenuToggle={handleConversationMenuToggle}
        onCloseMenu={() => {
          setOpenMenuChatId(null);
          setConversationMenuPosition(null);
        }}
        onOpenRename={openRename}
        onOpenDelete={(chat) => {
          setOpenMenuChatId(null);
          setConversationMenuPosition(null);
          setDeleteTarget(chat);
        }}
      />

      <section className="chat-canvas">
        <ModelPanel
          chatTitle={activeChat?.title ?? "Local AI Assistant"}
          health={lmHealth}
          theme={theme}
          onThemeChange={onThemeChange}
        />

        {error ? <ErrorBanner message={error} onClose={() => setError(null)} /> : null}

        <div className="message-thread-frame" style={threadFrameStyle}>
          <MessageThread
            messages={activeMessages}
            threadRef={messageThreadRef}
            onThreadScroll={handleMessageThreadScroll}
            recoveryEditorTextareaRef={recoveryEditorTextareaRef}
            latestAssistantId={latestAssistantId}
            unansweredLastUserId={unansweredLastUserId}
            pendingAssistant={pendingAssistant}
            isReasoningOpen={isReasoningOpen}
            editingUserMessageId={editingUserMessageId}
            editingUserContent={editingUserContent}
            copiedMessageId={copiedMessageId}
            isStreaming={isStreaming}
            isAssistantBusy={isAssistantBusy}
            selectedModelLoaded={selectedModelLoaded}
            maxLength={MAX_CONTEXT_CHARS}
            onCopy={handleMessageCopy}
            onRegenerate={handleMessageRegenerate}
            onStartEditLastUser={handleMessageStartEditLastUser}
            onEditingUserContentChange={setEditingUserContent}
            onRecoveryEditorKeyDown={handleMessageRecoveryEditorKeyDown}
            onSaveAndSendEditedLastUser={handleMessageSaveAndSendEditedLastUser}
            onCancelEditLastUser={handleMessageCancelEditLastUser}
            onRetryLastUser={handleMessageRetryLastUser}
            onReasoningToggle={handleMessageReasoningToggle}
          />
          <button className={"scroll-bottom-button " + (isThreadAtBottom ? "is-hidden" : "")} type="button" onClick={() => scrollThreadToBottom("smooth")} aria-label="Ugrás a legfrissebb üzenethez" title="Ugrás a legfrissebb üzenethez" aria-hidden={isThreadAtBottom ? true : undefined} tabIndex={isThreadAtBottom ? -1 : 0}>
            <ArrowDown size={18} aria-hidden="true" />
          </button>
        </div>

        <Composer
          textareaRef={composerTextareaRef}
          input={input}
          maxLength={MAX_CONTEXT_CHARS}
          reasoningEnabled={reasoningEnabled}
          activeToolMode={activeToolMode}
          isStreaming={isStreaming}
          canSend={canSend}
          warningText={composerWarningText}
          onInputChange={setInput}
          onReasoningToggle={handleReasoningToggle}
          onToolModeToggle={handleToolModeToggle}
          onStopStream={handleStopStream}
          onSubmit={handleSend}
          onKeyDown={handleComposerKeyDown}
        />
      </section>

      <ChatDialogs
        renameTarget={renameTarget}
        renameTitle={renameTitle}
        deleteTarget={deleteTarget}
        onRenameTitleChange={setRenameTitle}
        onRenameClose={() => setRenameTarget(null)}
        onRenameSubmit={handleRenameSubmit}
        onDeleteClose={() => setDeleteTarget(null)}
        onDeleteConfirm={() => void handleDeleteConfirm()}
      />
    </section>
  );
}


function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}
