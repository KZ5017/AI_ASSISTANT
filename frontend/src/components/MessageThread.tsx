import { memo, type KeyboardEvent, type Ref, type RefObject, type UIEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Pencil, RotateCcw, Send, X } from "lucide-react";

import { type AssistantMessage } from "../api/assistant";
import { type PendingMessage } from "./chatTypes";
import { ReasoningPanel } from "./ReasoningPanel";
import { SavedGraphRAGSourcesPanel } from "./SavedGraphRAGSourcesPanel";
import { SavedReasoningPanel } from "./SavedReasoningPanel";
import { SavedToolActivityPanel } from "./SavedToolActivityPanel";
import { SavedWorkNarrationPanel } from "./SavedWorkNarrationPanel";
import { ToolActivityPanel } from "./ToolActivityPanel";
import { TypingIndicator } from "./TypingIndicator";

type MessageThreadProps = {
  messages: Array<AssistantMessage | PendingMessage>;
  threadRef: RefObject<HTMLDivElement | null>;
  onThreadScroll: (event: UIEvent<HTMLDivElement>) => void;
  recoveryEditorTextareaRef: Ref<HTMLTextAreaElement>;
  latestAssistantId: number | undefined;
  unansweredLastUserId: number | null;
  pendingAssistant: PendingMessage | null;
  isReasoningOpen: boolean;
  editingUserMessageId: number | null;
  editingUserContent: string;
  copiedMessageId: number | null;
  isStreaming: boolean;
  isAssistantBusy: boolean;
  selectedModelLoaded: boolean;
  maxLength: number;
  onCopy: (message: AssistantMessage) => void;
  onRegenerate: () => void;
  onStartEditLastUser: (message: AssistantMessage) => void;
  onEditingUserContentChange: (value: string) => void;
  onRecoveryEditorKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSaveAndSendEditedLastUser: () => void;
  onCancelEditLastUser: () => void;
  onRetryLastUser: () => void;
  onReasoningToggle: () => void;
};

type MessageItemProps = {
  message: AssistantMessage | PendingMessage;
  isEditing: boolean;
  editingContent: string;
  isCopied: boolean;
  isLatestAssistant: boolean;
  isUnansweredLastUser: boolean;
  hasPendingAssistant: boolean;
  isReasoningOpen: boolean;
  isStreaming: boolean;
  isAssistantBusy: boolean;
  selectedModelLoaded: boolean;
  maxLength: number;
  recoveryEditorTextareaRef: Ref<HTMLTextAreaElement>;
  onCopy: (message: AssistantMessage) => void;
  onRegenerate: () => void;
  onStartEditLastUser: (message: AssistantMessage) => void;
  onEditingUserContentChange: (value: string) => void;
  onRecoveryEditorKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSaveAndSendEditedLastUser: () => void;
  onCancelEditLastUser: () => void;
  onRetryLastUser: () => void;
  onReasoningToggle: () => void;
};

const MessageItem = memo(function MessageItem({
  message,
  isEditing,
  editingContent,
  isCopied,
  isLatestAssistant,
  isUnansweredLastUser,
  hasPendingAssistant,
  isReasoningOpen,
  isStreaming,
  isAssistantBusy,
  selectedModelLoaded,
  maxLength,
  recoveryEditorTextareaRef,
  onCopy,
  onRegenerate,
  onStartEditLastUser,
  onEditingUserContentChange,
  onRecoveryEditorKeyDown,
  onSaveAndSendEditedLastUser,
  onCancelEditLastUser,
  onRetryLastUser,
  onReasoningToggle,
}: MessageItemProps) {
  const generationDurationLabel =
    typeof message.id === "number" && "generation_duration_ms" in message
      ? formatGenerationDuration(message.generation_duration_ms)
      : null;

  return (
    <article className={"message-row is-" + message.role}>
      <div className={"message-bubble " + (message.role === "user" && isEditing ? "is-editing" : "")}>
        {message.role === "assistant" ? (
          message.id === "pending-assistant" ? (
            <>
              <ReasoningPanel content={message.reasoningContent ?? ""} isOpen={isReasoningOpen} onToggle={onReasoningToggle} />
              <ToolActivityPanel content={message.toolActivityContent ?? ""} />
              {message.content.trim() !== "" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : null}
              <TypingIndicator />
            </>
          ) : (
            <>
              {typeof message.id === "number" && message.reasoning_content ? <SavedReasoningPanel content={message.reasoning_content} /> : null}
              {typeof message.id === "number" && message.tool_activity_content ? <SavedToolActivityPanel content={message.tool_activity_content} /> : null}
              {typeof message.id === "number" && message.work_narration_content ? <SavedWorkNarrationPanel content={message.work_narration_content} /> : null}
              {typeof message.id === "number" && message.graphrag ? <SavedGraphRAGSourcesPanel provenance={message.graphrag} /> : null}
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </>
          )
        ) : isEditing ? (
          <textarea ref={recoveryEditorTextareaRef} value={editingContent} maxLength={maxLength} rows={1} aria-label="User üzenet szerkesztése" onChange={(event) => onEditingUserContentChange(event.target.value)} onKeyDown={onRecoveryEditorKeyDown} autoFocus />
        ) : <div className="message-bubble__content"><p>{message.content}</p></div>}
      </div>
      {message.role === "assistant" && typeof message.id === "number" ? (
        <div className="message-actions">
          <button type="button" onClick={() => onCopy(message)} aria-label="Válasz másolása"><Copy size={15} aria-hidden="true" /> {isCopied ? "Másolva" : "Másolás"}</button>
          {isLatestAssistant ? <button type="button" onClick={onRegenerate} disabled={isStreaming || !selectedModelLoaded} aria-label="Válasz újragenerálása"><RotateCcw size={15} aria-hidden="true" /> Újragenerálás</button> : null}
          {generationDurationLabel ? <span className="message-action-meta" aria-label={"Válaszidő: " + generationDurationLabel}>{generationDurationLabel}</span> : null}
        </div>
      ) : null}
      {message.role === "user" && typeof message.id === "number" && isUnansweredLastUser && !hasPendingAssistant ? (
        <div className="message-actions">
          {isEditing ? (
            <>
              <button type="button" onClick={onSaveAndSendEditedLastUser} disabled={isAssistantBusy || !selectedModelLoaded || editingContent.trim() === ""} aria-label="Szerkesztett üzenet mentése és küldése"><Send size={15} aria-hidden="true" /> Mentés és küldés</button>
              <button type="button" onClick={onCancelEditLastUser} disabled={isAssistantBusy} aria-label="Szerkesztés megszakítása"><X size={15} aria-hidden="true" /> Mégse</button>
            </>
          ) : (
            <>
              <button type="button" onClick={() => onStartEditLastUser(message)} disabled={isAssistantBusy} aria-label="Üzenet szerkesztése"><Pencil size={15} aria-hidden="true" /> Szerkesztés</button>
              <button type="button" onClick={onRetryLastUser} disabled={isAssistantBusy || !selectedModelLoaded} aria-label="Üzenet újraküldése"><Send size={15} aria-hidden="true" /> Újraküldés</button>
            </>
          )}
        </div>
      ) : null}
    </article>
  );
});

function MessageThreadComponent({
  messages,
  threadRef,
  onThreadScroll,
  recoveryEditorTextareaRef,
  latestAssistantId,
  unansweredLastUserId,
  pendingAssistant,
  isReasoningOpen,
  editingUserMessageId,
  editingUserContent,
  copiedMessageId,
  isStreaming,
  isAssistantBusy,
  selectedModelLoaded,
  maxLength,
  onCopy,
  onRegenerate,
  onStartEditLastUser,
  onEditingUserContentChange,
  onRecoveryEditorKeyDown,
  onSaveAndSendEditedLastUser,
  onCancelEditLastUser,
  onRetryLastUser,
  onReasoningToggle,
}: MessageThreadProps) {
  if (messages.length === 0) {
    return (
      <div className="empty-thread">
        <p className="empty-title">Miben segíthetek?</p>
        <p className="empty-copy">
          Kérdezz szabadon általános módban, vagy válassz Tudásbázis, Adatbázis vagy GraphRAG módot rögzített forrásokhoz.{" "}
          <span className="empty-copy__emphasis">A Gondolkodó mód mindhárom forrásmóddal kombinálható.</span>
        </p>
      </div>
    );
  }

  return (
    <div className="message-thread" aria-live="polite" ref={threadRef as Ref<HTMLDivElement>} onScroll={onThreadScroll}>
      {messages.map((message) => {
        const isEditing = message.role === "user" && message.id === editingUserMessageId;
        return (
          <MessageItem
            key={message.id}
            message={message}
            isEditing={isEditing}
            editingContent={isEditing ? editingUserContent : ""}
            isCopied={typeof message.id === "number" && copiedMessageId === message.id}
            isLatestAssistant={typeof message.id === "number" && message.id === latestAssistantId}
            isUnansweredLastUser={typeof message.id === "number" && message.id === unansweredLastUserId}
            hasPendingAssistant={Boolean(pendingAssistant)}
            isReasoningOpen={message.id === "pending-assistant" ? isReasoningOpen : false}
            isStreaming={isStreaming}
            isAssistantBusy={isAssistantBusy}
            selectedModelLoaded={selectedModelLoaded}
            maxLength={maxLength}
            recoveryEditorTextareaRef={isEditing ? recoveryEditorTextareaRef : null}
            onCopy={onCopy}
            onRegenerate={onRegenerate}
            onStartEditLastUser={onStartEditLastUser}
            onEditingUserContentChange={onEditingUserContentChange}
            onRecoveryEditorKeyDown={onRecoveryEditorKeyDown}
            onSaveAndSendEditedLastUser={onSaveAndSendEditedLastUser}
            onCancelEditLastUser={onCancelEditLastUser}
            onRetryLastUser={onRetryLastUser}
            onReasoningToggle={onReasoningToggle}
          />
        );
      })}
    </div>
  );
}

function formatGenerationDuration(durationMs: number | null | undefined): string | null {
  if (typeof durationMs !== "number" || !Number.isFinite(durationMs) || durationMs < 0) {
    return null;
  }
  const totalSeconds = Math.round(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return minutes + ":" + seconds;
}

export const MessageThread = memo(MessageThreadComponent);
