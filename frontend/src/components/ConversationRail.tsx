import { type ChangeEvent, type MouseEvent, useMemo, useState } from "react";
import { CircleAlert, CircleCheck, MoreVertical, Pencil, Plus, RefreshCw, Search, Trash2 } from "lucide-react";

import { type AssistantChatSummary, type LMStudioHealth } from "../api/assistant";

type ConversationRailProps = {
  chats: AssistantChatSummary[];
  activeChatId: number | null;
  isLoading: boolean;
  isSending: boolean;
  health: LMStudioHealth | null;
  selectedModelLoaded: boolean;
  openMenuChatId: number | null;
  conversationMenuPosition: { top: number; left: number } | null;
  onCreateChat: () => void;
  onRefresh: () => void;
  onSelectChat: (chatId: number) => void;
  onMenuToggle: (chatId: number, event: MouseEvent<HTMLButtonElement>) => void;
  onCloseMenu: () => void;
  onOpenRename: (chat: AssistantChatSummary) => void;
  onOpenDelete: (chat: AssistantChatSummary) => void;
};

export function ConversationRail({
  chats,
  activeChatId,
  isLoading,
  isSending,
  health,
  selectedModelLoaded,
  openMenuChatId,
  conversationMenuPosition,
  onCreateChat,
  onRefresh,
  onSelectChat,
  onMenuToggle,
  onCloseMenu,
  onOpenRename,
  onOpenDelete,
}: ConversationRailProps) {
  const modelReady = health?.reachable === true && selectedModelLoaded;
  const statusText = modelReady ? "Modell betöltve" : "Modell hiba";
  const StatusIcon = modelReady ? CircleCheck : CircleAlert;
  const [filterText, setFilterText] = useState("");
  const normalizedFilterText = useMemo(() => normalizeChatTitle(filterText.trim()), [filterText]);
  const filteredChats = useMemo(
    () => chats.filter((chat) => normalizeChatTitle(chat.title).includes(normalizedFilterText)),
    [chats, normalizedFilterText],
  );

  function handleFilterChange(event: ChangeEvent<HTMLInputElement>) {
    setFilterText(event.target.value);
    onCloseMenu();
  }

  return (
    <aside className="conversation-rail">
      <div className="rail-header">
        <div className="rail-model-status" aria-label={statusText}>
          <span>{statusText}</span>
          <span className={"rail-model-status-icon " + (modelReady ? "is-ok" : "is-warning")} aria-hidden="true">
            <StatusIcon size={18} />
          </span>
        </div>
        <button className="primary-action" type="button" onClick={onCreateChat} disabled={isSending || isLoading}>
          <Plus size={18} aria-hidden="true" />
          Új beszélgetés
        </button>
        <button className="icon-button" type="button" aria-label="Frissítés" onClick={onRefresh}>
          <RefreshCw size={18} aria-hidden="true" />
        </button>
      </div>

      <div className="rail-filter">
        <div className="rail-filter__field">
          <Search className="rail-filter__icon" size={16} aria-hidden="true" />
          <input
            type="text"
            value={filterText}
            placeholder="Keresés..."
            aria-label="Beszélgetések szűrése"
            autoComplete="off"
            spellCheck={false}
            onChange={handleFilterChange}
          />
        </div>
      </div>

      <nav className="conversation-list" aria-label="Mentett beszélgetések">
        {filteredChats.map((chat) => (
          <div className="conversation-row" key={chat.id}>
            <button className={"conversation-item " + (activeChatId === chat.id ? "is-active" : "")} type="button" title={chat.title} onClick={() => onSelectChat(chat.id)}>
              <span>{chat.title}</span>
            </button>
            <button className="conversation-menu-button" type="button" aria-label="Beszélgetés menü" onClick={(event) => onMenuToggle(chat.id, event)}>
              <MoreVertical size={16} aria-hidden="true" />
            </button>
            {openMenuChatId === chat.id ? (
              <div className="conversation-menu" style={conversationMenuPosition ?? undefined}>
                <button type="button" onClick={() => onOpenRename(chat)}><Pencil size={15} aria-hidden="true" /> Átnevezés</button>
                <button type="button" className="danger-menu-item" onClick={() => onOpenDelete(chat)}><Trash2 size={15} aria-hidden="true" /> Törlés</button>
              </div>
            ) : null}
          </div>
        ))}
        {!isLoading && chats.length === 0 ? <p className="rail-empty">Nincs mentett beszélgetés.</p> : null}
        {!isLoading && chats.length > 0 && filteredChats.length === 0 ? <p className="rail-empty">Nincs találat.</p> : null}
      </nav>
    </aside>
  );
}

function normalizeChatTitle(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("hu-HU");
}
