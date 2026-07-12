import { type MouseEvent } from "react";
import { MoreVertical, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";

import { type AssistantChatSummary } from "../api/assistant";

type ConversationRailProps = {
  chats: AssistantChatSummary[];
  activeChatId: number | null;
  isLoading: boolean;
  isSending: boolean;
  openMenuChatId: number | null;
  conversationMenuPosition: { top: number; left: number } | null;
  onCreateChat: () => void;
  onRefreshChats: () => void;
  onSelectChat: (chatId: number) => void;
  onMenuToggle: (chatId: number, event: MouseEvent<HTMLButtonElement>) => void;
  onOpenRename: (chat: AssistantChatSummary) => void;
  onOpenDelete: (chat: AssistantChatSummary) => void;
};

export function ConversationRail({
  chats,
  activeChatId,
  isLoading,
  isSending,
  openMenuChatId,
  conversationMenuPosition,
  onCreateChat,
  onRefreshChats,
  onSelectChat,
  onMenuToggle,
  onOpenRename,
  onOpenDelete,
}: ConversationRailProps) {
  return (
    <aside className="conversation-rail">
      <div className="rail-header">
        <button className="primary-action" type="button" onClick={onCreateChat} disabled={isSending || isLoading}>
          <Plus size={18} aria-hidden="true" />
          Új beszélgetés
        </button>
        <button className="icon-button" type="button" aria-label="Beszélgetések frissítése" onClick={onRefreshChats}>
          <RefreshCw size={18} aria-hidden="true" />
        </button>
      </div>

      <nav className="conversation-list" aria-label="Mentett beszélgetések">
        {chats.map((chat) => (
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
      </nav>
    </aside>
  );
}
