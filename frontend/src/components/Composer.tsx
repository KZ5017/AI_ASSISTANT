import { type FormEvent, type KeyboardEvent, type Ref } from "react";
import { Send, Square } from "lucide-react";
import { type AssistantToolMode } from "../api/assistant";
import { ComposerModeBar } from "./ComposerModeBar";

type ComposerProps = {
  textareaRef: Ref<HTMLTextAreaElement>;
  input: string;
  maxLength: number;
  reasoningEnabled: boolean;
  activeToolMode: AssistantToolMode;
  isStreaming: boolean;
  canSend: boolean;
  warningText: string;
  onInputChange: (value: string) => void;
  onReasoningToggle: () => void;
  onToolModeToggle: (toolMode: AssistantToolMode) => void;
  onStopStream: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
};

export function Composer({
  textareaRef,
  input,
  maxLength,
  reasoningEnabled,
  activeToolMode,
  isStreaming,
  canSend,
  warningText,
  onInputChange,
  onReasoningToggle,
  onToolModeToggle,
  onStopStream,
  onSubmit,
  onKeyDown,
}: ComposerProps) {
  return (
    <form className="composer" aria-label="Üzenet küldése" onSubmit={onSubmit}>
      <div className="composer-input-slot">
        <textarea ref={textareaRef} rows={1} maxLength={maxLength} placeholder="Írj üzenetet..." aria-label="Üzenet szövege" value={input} onChange={(event) => onInputChange(event.target.value)} onKeyDown={onKeyDown} />
      </div>
      <button className="send-button" type={isStreaming ? "button" : "submit"} disabled={!isStreaming && !canSend} onClick={isStreaming ? onStopStream : undefined} aria-label={isStreaming ? "Leállítás" : "Küldés"} title={isStreaming ? "Leállítás" : "Küldés"}>
        {isStreaming ? <Square size={16} aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
      </button>
      <ComposerModeBar reasoningEnabled={reasoningEnabled} activeToolMode={activeToolMode} disabled={isStreaming} onReasoningToggle={onReasoningToggle} onToolModeToggle={onToolModeToggle} />
      <p className={"composer-warning " + (warningText ? "" : "is-hidden")} aria-live="polite" aria-hidden={warningText ? undefined : true}>
        {warningText || "Figyelmeztetés helye"}
      </p>
    </form>
  );
}
