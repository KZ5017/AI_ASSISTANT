export type AppNoticeType = "info" | "success" | "warning" | "error";

export type AppNotice = {
  type: AppNoticeType;
  message: string;
};

type ComposerWarningInput = {
  isPromptTooLong: boolean;
  isContextTooLong: boolean;
  selectedModelLoaded: boolean;
};

export function normalizeErrorMessage(error: unknown, fallback = "Váratlan hiba történt."): string {
  const rawMessage = error instanceof Error ? error.message : typeof error === "string" ? error : fallback;
  const message = rawMessage.trim();
  const lowerMessage = message.toLowerCase();

  if (message === "") {
    return fallback;
  }

  if (lowerMessage.includes("failed to fetch")) {
    return "A backend nem elérhető. Ellenőrizd, hogy fut-e az app backendje.";
  }

  if (lowerMessage.includes("networkerror") || lowerMessage.includes("network error")) {
    return "Hálózati vagy backend elérési hiba történt.";
  }

  if (message === "A böngésző nem adott olvasható streaming választ.") {
    return "A streaming válasz nem olvasható ebben a böngészőben.";
  }

  if (message === "LM Studio nem adott vissza végleges assistant választ.") {
    return "Az LM Studio nem adott végleges választ. Próbáld újraküldeni az üzenetet.";
  }

  if (looksLikeLMStudioConnectionError(lowerMessage)) {
    return "Az LM Studio nem válaszolt. Ellenőrizd, hogy fut-e, és be van-e töltve a modell.";
  }

  return message;
}

export function errorNotice(error: unknown, fallback?: string): AppNotice {
  return { type: "error", message: normalizeErrorMessage(error, fallback) };
}

export function successNotice(message: string): AppNotice {
  return { type: "success", message };
}

export function computeComposerWarning({ isPromptTooLong, isContextTooLong, selectedModelLoaded }: ComposerWarningInput): string {
  if (isPromptTooLong) {
    return "A prompt elérte a 120000 karakteres limitet.";
  }
  if (isContextTooLong) {
    return "A teljes beszélgetés és az új üzenet meghaladja a 120000 karakteres kontextuskeretet.";
  }
  if (!selectedModelLoaded) {
    return "Válassz ki és tölts be egy chat modellt az üzenetküldéshez.";
  }
  return "";
}

function looksLikeLMStudioConnectionError(message: string): boolean {
  return (
    message.includes("lm studio") && (
      message.includes("connection") ||
      message.includes("connect") ||
      message.includes("timeout") ||
      message.includes("timed out") ||
      message.includes("refused") ||
      message.includes("unreachable") ||
      message.includes("not reachable") ||
      message.includes("nem elérhető")
    )
  );
}
