import { type KeyboardEvent, type Ref, type RefObject, type UIEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Pencil, RotateCcw, Send, X } from "lucide-react";

import { type AssistantMessage } from "../api/assistant";
import { type PendingMessage } from "./chatTypes";
import { ReasoningPanel } from "./ReasoningPanel";
import { SavedReasoningPanel } from "./SavedReasoningPanel";
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

export function MessageThread({
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
        <p className="empty-copy">Indíts új beszélgetést, vagy írj rögtön egy üzenetet. Minden lokálisan fut az LM Studio mögött.</p>
      </div>
    );
  }

  return (
    <div className="message-thread" aria-live="polite" ref={threadRef as Ref<HTMLDivElement>} onScroll={onThreadScroll}>
      {messages.map((message) => (
        <article className={"message-row is-" + message.role} key={message.id}>
          <div className={"message-bubble " + (message.role === "user" && message.id === editingUserMessageId ? "is-editing" : "")}>
            {message.role === "assistant" ? (
              message.id === "pending-assistant" ? (
                <>
                  <ReasoningPanel content={message.reasoningContent ?? ""} isOpen={isReasoningOpen} onToggle={onReasoningToggle} />
                  {message.content === "" ? <TypingIndicator /> : <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>}
                </>
              ) : (
                <>
                  {typeof message.id === "number" && message.reasoning_content ? <SavedReasoningPanel content={message.reasoning_content} /> : null}
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </>
              )
            ) : message.id === editingUserMessageId ? (
              <textarea ref={recoveryEditorTextareaRef} value={editingUserContent} maxLength={maxLength} rows={1} aria-label="User üzenet szerkesztése" onChange={(event) => onEditingUserContentChange(event.target.value)} onKeyDown={onRecoveryEditorKeyDown} autoFocus />
            ) : <p>{message.content}</p>}
          </div>
          {message.role === "assistant" && typeof message.id === "number" ? (
            <div className="message-actions">
              <button type="button" onClick={() => onCopy(message)} aria-label="Válasz másolása"><Copy size={15} aria-hidden="true" /> {copiedMessageId === message.id ? "Másolva" : "Másolás"}</button>
              {message.id === latestAssistantId ? <button type="button" onClick={onRegenerate} disabled={isStreaming || !selectedModelLoaded} aria-label="Válasz újragenerálása"><RotateCcw size={15} aria-hidden="true" /> Újragenerálás</button> : null}
            </div>
          ) : null}
          {message.role === "user" && typeof message.id === "number" && message.id === unansweredLastUserId && !pendingAssistant ? (
            <div className="message-actions">
              {message.id === editingUserMessageId ? (
                <>
                  <button type="button" onClick={onSaveAndSendEditedLastUser} disabled={isAssistantBusy || !selectedModelLoaded || editingUserContent.trim() === ""} aria-label="Szerkesztett üzenet mentése és küldése"><Send size={15} aria-hidden="true" /> Mentés és küldés</button>
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
      ))}
    </div>
  );
}
