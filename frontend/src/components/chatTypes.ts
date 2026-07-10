import { type AssistantMessage } from "../api/assistant";

export type PendingMessage = Pick<AssistantMessage, "role" | "content" | "sequence_index"> & { id: "pending-user" | "pending-assistant"; reasoningContent?: string };
