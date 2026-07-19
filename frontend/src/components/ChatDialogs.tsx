import { type FormEvent } from "react";

import { type AssistantChatSummary } from "../api/assistant";

type ChatDialogsProps = {
  renameTarget: AssistantChatSummary | null;
  renameTitle: string;
  deleteTarget: AssistantChatSummary | null;
  onRenameTitleChange: (title: string) => void;
  onRenameClose: () => void;
  onRenameSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onDeleteClose: () => void;
  onDeleteConfirm: () => void;
};

export function ChatDialogs({
  renameTarget,
  renameTitle,
  deleteTarget,
  onRenameTitleChange,
  onRenameClose,
  onRenameSubmit,
  onDeleteClose,
  onDeleteConfirm,
}: ChatDialogsProps) {
  return (
    <>
      {renameTarget ? (
        <div className="dialog-backdrop" role="presentation" onMouseDown={onRenameClose}>
          <form className="app-dialog" aria-label="Beszélgetés átnevezése" onSubmit={onRenameSubmit} onMouseDown={(event) => event.stopPropagation()}>
            <h2>Átnevezés</h2>
            <input value={renameTitle} onChange={(event) => onRenameTitleChange(event.target.value)} maxLength={120} autoFocus />
            <div className="dialog-actions">
              <button type="button" className="secondary-action" onClick={onRenameClose}>Mégse</button>
              <button type="submit" className="primary-action">Mentés</button>
            </div>
          </form>
        </div>
      ) : null}

      {deleteTarget ? (
        <div className="dialog-backdrop" role="presentation" onMouseDown={onDeleteClose}>
          <div className="app-dialog" role="dialog" aria-modal="true" aria-label="Beszélgetés törlése" onMouseDown={(event) => event.stopPropagation()}>
            <h2>Törlés</h2>
            <p>Biztosan törlöd ezt a beszélgetést? A törlés véglegesen eltávolítja.</p>
            <div className="dialog-actions">
              <button type="button" className="secondary-action" onClick={onDeleteClose}>Mégse</button>
              <button type="button" className="danger-action" onClick={onDeleteConfirm}>Törlés</button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
