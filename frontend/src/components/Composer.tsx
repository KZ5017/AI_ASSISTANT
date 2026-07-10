import { type FormEvent, type KeyboardEvent, type Ref } from "react";
import { Lightbulb, LightbulbOff, Send, Square } from "lucide-react";

type ComposerProps = {
  textareaRef: Ref<HTMLTextAreaElement>;
  input: string;
  maxLength: number;
  reasoningEnabled: boolean;
  isStreaming: boolean;
  canSend: boolean;
  warningText: string;
  onInputChange: (value: string) => void;
  onReasoningToggle: () => void;
  onStopStream: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
};

export function Composer({
  textareaRef,
  input,
  maxLength,
  reasoningEnabled,
  isStreaming,
  canSend,
  warningText,
  onInputChange,
  onReasoningToggle,
  onStopStream,
  onSubmit,
  onKeyDown,
}: ComposerProps) {
  return (
    <form className="composer" aria-label="Üzenet küldése" onSubmit={onSubmit}>
      <div className="composer-input-slot">
        <textarea ref={textareaRef} rows={1} maxLength={maxLength} placeholder="Írj üzenetet..." aria-label="Üzenet szövege" value={input} onChange={(event) => onInputChange(event.target.value)} onKeyDown={onKeyDown} />
      </div>
      <button className={"reasoning-toggle " + (reasoningEnabled ? "is-active" : "")} type="button" aria-pressed={reasoningEnabled} onClick={onReasoningToggle} title={reasoningEnabled ? "Gondolkodó mód bekapcsolva" : "Gondolkodó mód kikapcsolva"}>
        {reasoningEnabled ? <Lightbulb size={17} aria-hidden="true" /> : <LightbulbOff size={17} aria-hidden="true" />}
        Gondolkodó
      </button>
      <button className="send-button" type={isStreaming ? "button" : "submit"} disabled={!isStreaming && !canSend} onClick={isStreaming ? onStopStream : undefined}>
        {isStreaming ? <Square size={16} aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
        {isStreaming ? "Leállítás" : "Küldés"}
      </button>
      <p className={"composer-warning " + (warningText ? "" : "is-hidden")} aria-live="polite" aria-hidden={warningText ? undefined : true}>
        {warningText || "Figyelmeztetés helye"}
      </p>
    </form>
  );
}
